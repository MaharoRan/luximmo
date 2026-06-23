from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO_ROOT))

from utils.geo_helpers import load_paris_iris, attach_iris_from_points, extract_paris_arrondissement

SILVER_DIR = REPO_ROOT / "Indicateur_3" / "silver"
GOLD_DIR = REPO_ROOT / "Indicateur_3" / "gold"

def _normalize_weights(series: pd.Series) -> pd.Series:
    maximum = series.max(skipna=True)
    if pd.isna(maximum) or maximum <= 0:
        return series * 0
    return series / maximum

def _load_hopitaux_scores() -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "hopitaux.parquet")
    df["arrondissement"] = df["cp_ville"].apply(extract_paris_arrondissement)
    df = df.dropna(subset=["arrondissement"]).copy()
    df["arrondissement"] = df["arrondissement"].astype(int)
    grouped = df.groupby("arrondissement", as_index=False).agg(hopitaux_count=("finess_et", "count"))
    grouped["hopitaux_raw"] = grouped["hopitaux_count"]
    return grouped

def _load_ecoles_scores(iris: pd.DataFrame, group_col: str) -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "etablissements-scolaires-ecoles-elementaires.parquet")
    df = attach_iris_from_points(df, "longitude", "latitude", iris)
    grouped = df.groupby(group_col, as_index=False).agg(ecoles_count=("id_projet", "count"))
    grouped["ecoles_raw"] = grouped["ecoles_count"]
    return grouped

def _load_pharmacies_scores() -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "pharmacies.parquet")
    df["arrondissement"] = df["cp"].apply(extract_paris_arrondissement)
    df = df.dropna(subset=["arrondissement"]).copy()
    df["arrondissement"] = df["arrondissement"].astype(int)
    grouped = df.groupby("arrondissement", as_index=False).agg(pharmacies_count=("nofinesset", "count"))
    grouped["pharmacies_raw"] = grouped["pharmacies_count"]
    return grouped

def _load_police_scores() -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "carte-des-points-daccueil-police-a-paris.parquet")
    df["arrondissement"] = df["ardt"].apply(extract_paris_arrondissement)
    df = df.dropna(subset=["arrondissement"]).copy()
    df["arrondissement"] = df["arrondissement"].astype(int)
    grouped = df.groupby("arrondissement", as_index=False).agg(police_count=("service", "count"))
    grouped["police_raw"] = grouped["police_count"]
    return grouped

def _load_postes_scores(iris: pd.DataFrame, group_col: str) -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "les_bureaux_de_poste_et_agences_postales_en_idf.parquet")
    df = attach_iris_from_points(df, "longitude", "latitude", iris)
    grouped = df.groupby(group_col, as_index=False).agg(postes_count=("libelle_du_site", "count"))
    grouped["postes_raw"] = grouped["postes_count"]
    return grouped

def _load_bibliotheques_scores(iris: pd.DataFrame, group_col: str) -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "postes-publics-des-bibliotheques.parquet")
    df = attach_iris_from_points(df, "longitude", "latitude", iris)
    grouped = df.groupby(group_col, as_index=False).agg(biblio_count=("localisation", "count"))
    grouped["biblio_raw"] = grouped["biblio_count"]
    return grouped

def build_score_df(iris: pd.DataFrame, group_col: str, base_df: pd.DataFrame) -> pd.DataFrame:
    hopitaux = _load_hopitaux_scores()
    pharmacies = _load_pharmacies_scores()
    police = _load_police_scores()
    
    ecoles = _load_ecoles_scores(iris, group_col)
    postes = _load_postes_scores(iris, group_col)
    biblio = _load_bibliotheques_scores(iris, group_col)

    score = base_df.copy()
    score = score.merge(hopitaux, on="arrondissement", how="left")
    score = score.merge(pharmacies, on="arrondissement", how="left")
    score = score.merge(police, on="arrondissement", how="left")
    
    score = score.merge(ecoles, on=group_col, how="left")
    score = score.merge(postes, on=group_col, how="left")
    score = score.merge(biblio, on=group_col, how="left")

    numeric_columns = [
        "hopitaux_count", "hopitaux_raw",
        "ecoles_count", "ecoles_raw",
        "pharmacies_count", "pharmacies_raw",
        "police_count", "police_raw",
        "postes_count", "postes_raw",
        "biblio_count", "biblio_raw",
    ]
    for column in numeric_columns:
        if column not in score.columns:
            score[column] = 0
        score[column] = score[column].fillna(0)

    score["hopitaux_norm"] = _normalize_weights(score["hopitaux_raw"]) 
    score["ecoles_norm"] = _normalize_weights(score["ecoles_raw"]) 
    score["pharmacies_norm"] = _normalize_weights(score["pharmacies_raw"]) 
    score["police_norm"] = _normalize_weights(score["police_raw"]) 
    score["postes_norm"] = _normalize_weights(score["postes_raw"]) 
    score["biblio_norm"] = _normalize_weights(score["biblio_raw"]) 

    raw_final = (
        0.30 * score["hopitaux_norm"]
        + 0.30 * score["ecoles_norm"]
        + 0.15 * score["pharmacies_norm"]
        + 0.12 * score["police_norm"]
        + 0.08 * score["postes_norm"]
        + 0.05 * score["biblio_norm"]
    )
    
    s_min = raw_final.min()
    s_max = raw_final.max()
    if s_max > s_min:
        score["score_acces_services_publiques"] = (20 + 80 * (raw_final - s_min) / (s_max - s_min)).round(2)
    else:
        score["score_acces_services_publiques"] = 50.0

    score = score.sort_values("score_acces_services_publiques", ascending=False).reset_index(drop=True)
    return score

def build_gold_scores() -> tuple[pd.DataFrame, pd.DataFrame]:
    iris = load_paris_iris()
    
    arr_base = pd.DataFrame({"arrondissement": list(range(1, 21))})
    score_arr = build_score_df(iris, "arrondissement", arr_base)
    score_arr["arrondissement_libelle"] = score_arr["arrondissement"].apply(lambda value: f"Paris {int(value)}e Arrondissement")
    
    iris_base = iris[["code_iris", "nom_iris", "arrondissement", "nom_com"]].drop_duplicates()
    score_iris = build_score_df(iris, "code_iris", iris_base)
    
    return score_arr, score_iris

def main() -> None:
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    score_arr, score_iris = build_gold_scores()
    
    path_arr = GOLD_DIR / "score_acces_services_publiques.parquet"
    score_arr.to_parquet(path_arr, index=False)
    print(f"Ecrit: {path_arr}")
    
    path_iris = GOLD_DIR / "score_acces_services_publiques_iris.parquet"
    score_iris.to_parquet(path_iris, index=False)
    print(f"Ecrit: {path_iris}")

if __name__ == "__main__":
    main()
