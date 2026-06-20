from __future__ import annotations

from pathlib import Path
import re

import pandas as pd
from shapely import wkb
from shapely.geometry import Point
from shapely.strtree import STRtree


REPO_ROOT = Path(__file__).resolve().parents[1]
GEO_DIR = REPO_ROOT / "geo"
SILVER_DIR = REPO_ROOT / "Indicateur_2" / "silver"
GOLD_DIR = REPO_ROOT / "Indicateur_2" / "gold"

PARIS_ARRONDISSEMENT_RE = re.compile(r"Paris\s+(\d{1,2})e\s+Arrondissement", re.IGNORECASE)
POSTAL_75_RE = re.compile(r"75(\d{3})")

EVENT_KEYWORDS = {
    "restaurants": [r"\brestaurant\b", r"\brestaurants\b"],
    "bars": [r"\bbar\b", r"\bbars\b"],
    "discotheques": [r"discoth[eè]que", r"discotheques?"],
    "musees": [r"mus[ée]e", r"musees?"],
    "cinema": [r"cin[eé]ma", r"cinemas?"],
    "theatres": [r"th[eé]atre", r"theatres?"],
}


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

    match = POSTAL_75_RE.search(text)
    if match:
        arrondissement = int(match.group(1)) % 100
        if 1 <= arrondissement <= 20:
            return arrondissement

    if text.isdigit():
        arrondissement = int(text)
        if 1 <= arrondissement <= 20:
            return arrondissement

    match = re.search(r"(\d{1,2})", text)
    if match:
        arrondissement = int(match.group(1))
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


def _keyword_score(text: str) -> float:
    lowered = str(text).lower()
    if not lowered or lowered == "nan":
        return 0.0

    score = 0.0
    for patterns in EVENT_KEYWORDS.values():
        if any(re.search(pattern, lowered) for pattern in patterns):
            score += 1.0
    return score


def _score_event_weight(text: str) -> float:
    lowered = str(text).lower()
    if not lowered or lowered == "nan":
        return 0.0

    if re.search(r"\b(restaurant|bar|discoth[eè]que)\b", lowered):
        return 1.35
    if re.search(r"\b(mus[ée]e|cin[eé]ma|th[eé]atre)\b", lowered):
        return 1.15
    return 0.25 if _keyword_score(lowered) > 0 else 0.0


def _load_activities_scores() -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "que-faire-a-paris.parquet")
    df = df.copy()
    combined_text = df["title"].astype(str).fillna("") + " " + df["address_name"].astype(str).fillna("")
    df["arrondissement"] = combined_text.apply(_extract_paris_arrondissement)
    df = df.dropna(subset=["arrondissement"]).copy()
    df["arrondissement"] = df["arrondissement"].astype(int)
    df["event_weight"] = combined_text.apply(_score_event_weight)

    grouped = df.groupby("arrondissement", as_index=False).agg(
        activities_count=("id", "count"),
        activities_weight=("event_weight", "sum"),
    )
    grouped["activities_raw"] = grouped["activities_count"] * 0.7 + grouped["activities_weight"]
    return grouped


def _load_voirie_activity_scores(iris: pd.DataFrame) -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "plan de voirie.parquet")
    df = _attach_arrondissement_from_points(df, "longitude", "latitude", iris)
    grouped = df.groupby("arrondissement", as_index=False).agg(voirie_activity_segments=("OBJECTID", "count"))
    grouped["voirie_activity_raw"] = grouped["voirie_activity_segments"]
    return grouped


def _load_green_space_scores() -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "les-arbres.parquet")
    df = df.copy()
    df["arrondissement"] = df["arrondissement"].apply(_extract_paris_arrondissement)
    df = df.dropna(subset=["arrondissement"]).copy()
    df["arrondissement"] = df["arrondissement"].astype(int)

    grouped = df.groupby("arrondissement", as_index=False).agg(
        trees_count=("arrondissement", "count"),
    )
    grouped["trees_raw"] = grouped["trees_count"]
    return grouped


def _load_freshness_islands_scores() -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "ilots-de-fraicheur-espaces-verts-frais.parquet")
    df = df.copy()
    df["arrondissement"] = df["arrondissement"].apply(_extract_paris_arrondissement)
    if "longitude" in df.columns and "latitude" in df.columns:
        df["longitude"] = _safe_numeric_series(df["longitude"])
        df["latitude"] = _safe_numeric_series(df["latitude"])
    df = df.dropna(subset=["arrondissement"]).copy()
    df["arrondissement"] = df["arrondissement"].astype(int)

    grouped = df.groupby("arrondissement", as_index=False).agg(
        islands_count=("nom", "count"),
    )
    grouped["islands_raw"] = grouped["islands_count"]
    return grouped


def _load_association_scores() -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "liste_des_associations_parisiennes.parquet")
    df = df.copy()
    df["arrondissement"] = df["cp_adresse_code_postal"].apply(_extract_paris_arrondissement)
    df = df.dropna(subset=["arrondissement"]).copy()
    df["arrondissement"] = df["arrondissement"].astype(int)
    grouped = df.groupby("arrondissement", as_index=False).agg(associations_count=("pr_nom_statutaire", "count"))
    grouped["associations_raw"] = grouped["associations_count"]
    return grouped


def _load_film_scores() -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "lieux-de-tournage-a-paris.parquet")
    df = df.copy()
    df["arrondissement"] = df["ardt_lieu"].apply(_extract_paris_arrondissement)
    df = df.dropna(subset=["arrondissement"]).copy()
    df["arrondissement"] = df["arrondissement"].astype(int)
    grouped = df.groupby("arrondissement", as_index=False).agg(film_locations=("id_lieu", "count"))
    grouped["film_raw"] = grouped["film_locations"]
    return grouped


def _load_tourism_scores(iris: pd.DataFrame) -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "zones-touristiques-internationales.parquet")
    df = _attach_arrondissement_from_points(df, "longitude", "latitude", iris)
    grouped = df.groupby("arrondissement", as_index=False).agg(tourism_zones=("name", "count"))
    grouped["tourism_raw"] = grouped["tourism_zones"]
    return grouped


def build_gold_score() -> pd.DataFrame:
    iris = _load_paris_iris()

    activities = _load_activities_scores()
    voirie_activity = _load_voirie_activity_scores(iris)
    green_space = _load_green_space_scores()
    islands = _load_freshness_islands_scores()
    associations = _load_association_scores()
    films = _load_film_scores()
    tourism = _load_tourism_scores(iris)

    score = pd.DataFrame({"arrondissement": list(range(1, 21))})
    score = score.merge(activities, on="arrondissement", how="left")
    score = score.merge(voirie_activity, on="arrondissement", how="left")
    score = score.merge(green_space, on="arrondissement", how="left")
    score = score.merge(islands, on="arrondissement", how="left")
    score = score.merge(associations, on="arrondissement", how="left")
    score = score.merge(films, on="arrondissement", how="left")
    score = score.merge(tourism, on="arrondissement", how="left")

    numeric_columns = [
        "activities_count",
        "activities_weight",
        "activities_raw",
        "voirie_activity_segments",
        "voirie_activity_raw",
        "trees_count",
        "trees_raw",
        "islands_count",
        "islands_raw",
        "associations_count",
        "associations_raw",
        "film_locations",
        "film_raw",
        "tourism_zones",
        "tourism_raw",
    ]
    for column in numeric_columns:
        if column not in score.columns:
            score[column] = 0
        score[column] = score[column].fillna(0)

    score["activities_norm"] = _normalize_weights(score["activities_raw"])
    score["voirie_activity_norm"] = _normalize_weights(score["voirie_activity_raw"])
    score["trees_norm"] = _normalize_weights(score["trees_raw"])
    score["islands_norm"] = _normalize_weights(score["islands_raw"])
    score["associations_norm"] = _normalize_weights(score["associations_raw"])
    score["film_norm"] = _normalize_weights(score["film_raw"])
    score["tourism_norm"] = _normalize_weights(score["tourism_raw"])

    score["score_interet_culturel_loisir"] = (
        100
        * (
            0.25 * score["activities_norm"]
            + 0.25 * score["voirie_activity_norm"]
            + 0.20 * score["associations_norm"]
            + 0.10 * score["trees_norm"]
            + 0.10 * score["islands_norm"]
            + 0.05 * score["film_norm"]
            + 0.05 * score["tourism_norm"]
        )
    ).round(2)

    score["arrondissement_libelle"] = score["arrondissement"].apply(lambda value: f"Paris {int(value)}e Arrondissement")
    score = score.sort_values("score_interet_culturel_loisir", ascending=False).reset_index(drop=True)

    return score[
        [
            "arrondissement",
            "arrondissement_libelle",
            "score_interet_culturel_loisir",
            "activities_count",
            "activities_weight",
            "voirie_activity_segments",
            "trees_count",
            "islands_count",
            "associations_count",
            "film_locations",
            "tourism_zones",
            "activities_norm",
            "voirie_activity_norm",
            "trees_norm",
            "islands_norm",
            "associations_norm",
            "film_norm",
            "tourism_norm",
        ]
    ]


def main() -> None:
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    score = build_gold_score()
    output_path = GOLD_DIR / "score_interet_culturel_loisir.parquet"
    score.to_parquet(output_path, index=False)
    print(f"Ecrit: {output_path}")


if __name__ == "__main__":
    main()
