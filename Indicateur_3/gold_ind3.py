from __future__ import annotations

from pathlib import Path
import re

import pandas as pd
from shapely.geometry import Point
from shapely.strtree import STRtree
from shapely import wkb


REPO_ROOT = Path(__file__).resolve().parents[1]
GEO_DIR = REPO_ROOT / "geo"
SILVER_DIR = REPO_ROOT / "Indicateur_3" / "silver"
GOLD_DIR = REPO_ROOT / "Indicateur_3" / "gold"


PARIS_ARRONDISSEMENT_RE = re.compile(r"Paris\s+(\d{1,2})e\s+Arrondissement", re.IGNORECASE)
POSTAL_75_RE = re.compile(r"75(\d{3})")


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

    # try postal code like 75001, 75010, or '75001 PARIS'
    match = POSTAL_75_RE.search(text)
    if match:
        code = int(match.group(1))
        arrondissement = code % 100
        if 1 <= arrondissement <= 20:
            return arrondissement

    # fallback: if the value is digits and within 1..20
    if text.isdigit():
        arrondissement = int(text)
        if 1 <= arrondissement <= 20:
            return arrondissement

    # try to find first 1-2 digit number in text
    m = re.search(r"(\d{1,2})", text)
    if m:
        arrondissement = int(m.group(1))
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


def _load_hopitaux_scores() -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "hopitaux.parquet")
    df = df.copy()
    df["arrondissement"] = df["cp_ville"].apply(_extract_paris_arrondissement)
    df = df.dropna(subset=["arrondissement"]).copy()
    df["arrondissement"] = df["arrondissement"].astype(int)
    grouped = df.groupby("arrondissement", as_index=False).agg(hopitaux_count=("finess_et", "count"))
    grouped["hopitaux_raw"] = grouped["hopitaux_count"]
    return grouped


def _load_ecoles_scores(iris: pd.DataFrame) -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "etablissements-scolaires-ecoles-elementaires.parquet")
    df = _attach_arrondissement_from_points(df, "longitude", "latitude", iris)
    grouped = df.groupby("arrondissement", as_index=False).agg(ecoles_count=("id_projet", "count"))
    grouped["ecoles_raw"] = grouped["ecoles_count"]
    return grouped


def _load_pharmacies_scores() -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "pharmacies.parquet")
    df = df.copy()
    df["arrondissement"] = df["cp"].apply(_extract_paris_arrondissement)
    df = df.dropna(subset=["arrondissement"]).copy()
    df["arrondissement"] = df["arrondissement"].astype(int)
    grouped = df.groupby("arrondissement", as_index=False).agg(pharmacies_count=("nofinesset", "count"))
    grouped["pharmacies_raw"] = grouped["pharmacies_count"]
    return grouped


def _load_police_scores() -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "carte-des-points-daccueil-police-a-paris.parquet")
    df = df.copy()
    df["arrondissement"] = df["ardt"].apply(_extract_paris_arrondissement)
    df = df.dropna(subset=["arrondissement"]).copy()
    df["arrondissement"] = df["arrondissement"].astype(int)
    grouped = df.groupby("arrondissement", as_index=False).agg(police_count=("service", "count"))
    grouped["police_raw"] = grouped["police_count"]
    return grouped


def _load_postes_scores(iris: pd.DataFrame) -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "les_bureaux_de_poste_et_agences_postales_en_idf.parquet")
    df = _attach_arrondissement_from_points(df, "longitude", "latitude", iris)
    grouped = df.groupby("arrondissement", as_index=False).agg(postes_count=("libelle_du_site", "count"))
    grouped["postes_raw"] = grouped["postes_count"]
    return grouped


def _load_bibliotheques_scores(iris: pd.DataFrame) -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "postes-publics-des-bibliotheques.parquet")
    df = _attach_arrondissement_from_points(df, "longitude", "latitude", iris)
    grouped = df.groupby("arrondissement", as_index=False).agg(biblio_count=("localisation", "count"))
    grouped["biblio_raw"] = grouped["biblio_count"]
    return grouped


def build_gold_score() -> pd.DataFrame:
    iris = _load_paris_iris()

    hopitaux = _load_hopitaux_scores()
    ecoles = _load_ecoles_scores(iris)
    pharmacies = _load_pharmacies_scores()
    police = _load_police_scores()
    postes = _load_postes_scores(iris)
    biblio = _load_bibliotheques_scores(iris)

    score = pd.DataFrame({"arrondissement": list(range(1, 21))})
    score = score.merge(hopitaux, on="arrondissement", how="left")
    score = score.merge(ecoles, on="arrondissement", how="left")
    score = score.merge(pharmacies, on="arrondissement", how="left")
    score = score.merge(police, on="arrondissement", how="left")
    score = score.merge(postes, on="arrondissement", how="left")
    score = score.merge(biblio, on="arrondissement", how="left")

    numeric_columns = [
        "hopitaux_count",
        "hopitaux_raw",
        "ecoles_count",
        "ecoles_raw",
        "pharmacies_count",
        "pharmacies_raw",
        "police_count",
        "police_raw",
        "postes_count",
        "postes_raw",
        "biblio_count",
        "biblio_raw",
    ]
    for column in numeric_columns:
        if column not in score.columns:
            score[column] = 0
        score[column] = score[column].fillna(0)

    # normalize each raw metric
    score["hopitaux_norm"] = _normalize_weights(score["hopitaux_raw"]) 
    score["ecoles_norm"] = _normalize_weights(score["ecoles_raw"]) 
    score["pharmacies_norm"] = _normalize_weights(score["pharmacies_raw"]) 
    score["police_norm"] = _normalize_weights(score["police_raw"]) 
    score["postes_norm"] = _normalize_weights(score["postes_raw"]) 
    score["biblio_norm"] = _normalize_weights(score["biblio_raw"]) 

    # weights: hopitaux > ecoles > pharmacies > police > postes > biblio
    score["score_acces_services_publiques"] = (
        100
        * (
            0.30 * score["hopitaux_norm"]
            + 0.30 * score["ecoles_norm"]
            + 0.15 * score["pharmacies_norm"]
            + 0.12 * score["police_norm"]
            + 0.08 * score["postes_norm"]
            + 0.05 * score["biblio_norm"]
        )
    ).round(2)

    score["arrondissement_libelle"] = score["arrondissement"].apply(lambda value: f"Paris {int(value)}e Arrondissement")
    score = score.sort_values("score_acces_services_publiques", ascending=False).reset_index(drop=True)

    return score[
        [
            "arrondissement",
            "arrondissement_libelle",
            "score_acces_services_publiques",
            "hopitaux_count",
            "ecoles_count",
            "pharmacies_count",
            "police_count",
            "postes_count",
            "biblio_count",
            "hopitaux_norm",
            "ecoles_norm",
            "pharmacies_norm",
            "police_norm",
            "postes_norm",
            "biblio_norm",
        ]
    ]


def main() -> None:
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    score = build_gold_score()
    output_path = GOLD_DIR / "score_acces_services_publiques.parquet"
    score.to_parquet(output_path, index=False)
    print(f"Ecrit: {output_path}")


if __name__ == "__main__":
    main()
