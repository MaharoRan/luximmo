from __future__ import annotations

from pathlib import Path
import re

import pandas as pd
from shapely.geometry import Point
from shapely.strtree import STRtree
from shapely import wkb


REPO_ROOT = Path(__file__).resolve().parents[1]
GEO_DIR = REPO_ROOT / "geo"
SILVER_DIR = REPO_ROOT / "Indicateur_4" / "silver"
GOLD_DIR = REPO_ROOT / "Indicateur_4" / "gold"

PARIS_ARRONDISSEMENT_RE = re.compile(r"Paris\s+(\d{1,2})e\s+Arrondissement", re.IGNORECASE)


def _safe_numeric_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


def _extract_paris_arrondissement(value) -> int | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    match = PARIS_ARRONDISSEMENT_RE.search(text)
    if match:
        arrondissement = int(match.group(1))
        if 1 <= arrondissement <= 20:
            return arrondissement

    if text.isdigit():
        arrondissement = int(text)
        if 1 <= arrondissement <= 20:
            return arrondissement

    return None


def _load_paris_iris() -> pd.DataFrame:
    iris = pd.read_parquet(GEO_DIR / "iris.parquet")
    iris = iris[iris["nom_com"].astype(str).str.contains("Paris", case=False, na=False)].copy()
    iris["arrondissement"] = iris["nom_com"].apply(_extract_paris_arrondissement)
    iris["geometry"] = iris["geo_shape"].apply(lambda value: wkb.loads(bytes(value)) if pd.notna(value) else None)
    iris = iris.dropna(subset=["arrondissement", "geometry"]).copy()
    iris["arrondissement"] = iris["arrondissement"].astype(int)
    return iris[["code_iris", "nom_iris", "nom_com", "arrondissement", "geometry"]]


def _attach_arrondissement_from_points(df: pd.DataFrame, lon_col: str, lat_col: str, iris: pd.DataFrame) -> pd.DataFrame:
    working = df.copy()
    working[lon_col] = _safe_numeric_series(working[lon_col])
    working[lat_col] = _safe_numeric_series(working[lat_col])
    working = working.dropna(subset=[lon_col, lat_col]).copy()
    if working.empty:
        working["arrondissement"] = pd.Series(dtype="int64")
        return working

    iris_geometries = iris["geometry"].tolist()
    iris_arrondissements = iris["arrondissement"].tolist()
    iris_lookup = {geometry.wkb: arrondissement for geometry, arrondissement in zip(iris_geometries, iris_arrondissements)}
    tree = STRtree(iris_geometries)

    arrondissements: list[int | None] = []
    for longitude, latitude in zip(working[lon_col], working[lat_col]):
        point = Point(float(longitude), float(latitude))
        arrondissement = None
        for candidate in tree.query(point):
            if hasattr(candidate, "covers"):
                geometry = candidate
                candidate_arrondissement = iris_lookup.get(candidate.wkb)
            else:
                geometry = iris_geometries[int(candidate)]
                candidate_arrondissement = iris_arrondissements[int(candidate)]

            if geometry.covers(point):
                arrondissement = candidate_arrondissement
                break

        arrondissements.append(arrondissement)

    working["arrondissement"] = arrondissements
    working = working.dropna(subset=["arrondissement"]).copy()
    working["arrondissement"] = working["arrondissement"].astype(int)
    return working


def _normalize_weights(series: pd.Series) -> pd.Series:
    maximum = series.max(skipna=True)
    if pd.isna(maximum) or maximum <= 0:
        return series * 0
    return series / maximum


def _load_gare_scores(iris: pd.DataFrame) -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "emplacement-des-gares-idf.parquet")
    df = _attach_arrondissement_from_points(df, "longitude", "latitude", iris)
    if "capacity" in df.columns:
        df["capacity"] = _safe_numeric_series(df["capacity"]).fillna(0)
    else:
        df["capacity"] = 0

    grouped = df.groupby("arrondissement", as_index=False).agg(
        gare_stations=("gares_id", "count"),
        gare_capacity=("capacity", "sum"),
    )
    grouped["gare_raw"] = grouped["gare_stations"] * 2 + grouped["gare_capacity"] / 40.0
    return grouped


def _load_velib_scores(iris: pd.DataFrame) -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "velib-emplacement-des-stations.parquet")
    df = _attach_arrondissement_from_points(df, "longitude", "latitude", iris)
    if "capacity" in df.columns:
        df["capacity"] = _safe_numeric_series(df["capacity"]).fillna(0)
    else:
        df["capacity"] = 0

    grouped = df.groupby("arrondissement", as_index=False).agg(
        velib_stations=("stationcode", "count"),
        velib_capacity=("capacity", "sum"),
    )
    grouped["velib_raw"] = grouped["velib_stations"] + grouped["velib_capacity"] / 60.0
    return grouped


def _amenagement_weight(value, coronapiste) -> float:
    text = str(value).lower() if value is not None else ""
    if "piste cyclable" in text or "voie verte" in text:
        weight = 1.0
    elif "bande cyclable" in text:
        weight = 0.8
    elif "couloir bus ouvert aux vélos" in text:
        weight = 0.7
    elif "voie piétonne" in text:
        weight = 0.35
    elif text and text != "nan":
        weight = 0.5
    else:
        weight = 0.0

    if str(coronapiste).strip().lower() == "oui":
        weight += 0.2

    return weight


def _load_cycling_scores() -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "amenagements-cyclables.parquet")
    df = df.copy()
    df["arrondissement"] = df["arrondissement"].apply(_extract_paris_arrondissement)
    df = df.dropna(subset=["arrondissement"]).copy()
    df["arrondissement"] = df["arrondissement"].astype(int)
    df["cycling_weight"] = df.apply(lambda row: _amenagement_weight(row.get("amenagement"), row.get("coronapiste")), axis=1)

    grouped = df.groupby("arrondissement", as_index=False).agg(
        cycling_segments=("osm_id", "count"),
        cycling_weight=("cycling_weight", "sum"),
    )
    grouped["cycling_raw"] = grouped["cycling_weight"]
    return grouped


def _load_transport_proxy_scores(iris: pd.DataFrame) -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "plan de voirie.parquet")
    df = _attach_arrondissement_from_points(df, "longitude", "latitude", iris)

    grouped = df.groupby("arrondissement", as_index=False).agg(
        transport_segments=("OBJECTID", "count"),
    )
    grouped["transport_raw"] = grouped["transport_segments"]
    return grouped


def build_gold_score() -> pd.DataFrame:
    iris = _load_paris_iris()

    gare_scores = _load_gare_scores(iris)
    velib_scores = _load_velib_scores(iris)
    cycling_scores = _load_cycling_scores()
    transport_scores = _load_transport_proxy_scores(iris)

    score = pd.DataFrame({"arrondissement": list(range(1, 21))})
    score = score.merge(gare_scores, on="arrondissement", how="left")
    score = score.merge(velib_scores, on="arrondissement", how="left")
    score = score.merge(cycling_scores, on="arrondissement", how="left")
    score = score.merge(transport_scores, on="arrondissement", how="left")

    numeric_columns = [
        "gare_stations",
        "gare_capacity",
        "gare_raw",
        "velib_stations",
        "velib_capacity",
        "velib_raw",
        "cycling_segments",
        "cycling_weight",
        "cycling_raw",
        "transport_segments",
        "transport_raw",
    ]
    for column in numeric_columns:
        if column not in score.columns:
            score[column] = 0
        score[column] = score[column].fillna(0)

    score["gare_norm"] = _normalize_weights(score["gare_raw"])
    score["velib_norm"] = _normalize_weights(score["velib_raw"])
    score["cycling_norm"] = _normalize_weights(score["cycling_raw"])
    score["transport_norm"] = _normalize_weights(score["transport_raw"])

    score["score_acces_transport"] = (
        100
        * (
            0.45 * score["gare_norm"]
            + 0.30 * score["transport_norm"]
            + 0.15 * score["velib_norm"]
            + 0.10 * score["cycling_norm"]
        )
    ).round(2)

    score["arrondissement_libelle"] = score["arrondissement"].apply(lambda value: f"Paris {int(value)}e Arrondissement")
    score = score.sort_values("score_acces_transport", ascending=False).reset_index(drop=True)
    return score[
        [
            "arrondissement",
            "arrondissement_libelle",
            "score_acces_transport",
            "gare_stations",
            "gare_capacity",
            "velib_stations",
            "velib_capacity",
            "cycling_segments",
            "cycling_weight",
            "transport_segments",
            "gare_norm",
            "velib_norm",
            "cycling_norm",
            "transport_norm",
        ]
    ]


def main() -> None:
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    score = build_gold_score()
    output_path = GOLD_DIR / "score_acces_transport.parquet"
    score.to_parquet(output_path, index=False)
    print(f"Ecrit: {output_path}")


if __name__ == "__main__":
    main()