from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO_ROOT))

from utils.geo_helpers import load_paris_iris, attach_iris_from_points, extract_paris_arrondissement

SILVER_DIR = REPO_ROOT / "Indicateur_1" / "silver"
GOLD_DIR = REPO_ROOT / "Indicateur_1" / "gold"

def _normalize_weights(series: pd.Series) -> pd.Series:
    maximum = series.max(skipna=True)
    if pd.isna(maximum) or maximum <= 0:
        return series * 0
    return series / maximum

def _load_trees_scores(iris: pd.DataFrame, group_col: str) -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "les-arbres.parquet")
    df = attach_iris_from_points(df, "longitude", "latitude", iris)
    grouped = df.groupby(group_col, as_index=False).agg(trees_count=(group_col, "count"))
    grouped["trees_raw"] = grouped["trees_count"]
    return grouped

def _load_freshness_islands_scores(iris: pd.DataFrame, group_col: str) -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "ilots-de-fraicheur-espaces-verts-frais.parquet")
    if "longitude" in df.columns and "latitude" in df.columns:
        df = attach_iris_from_points(df, "longitude", "latitude", iris)
    else:
        df[group_col] = None # Fallback (should not happen based on silver analysis)
    
    df = df.dropna(subset=[group_col]).copy()
    grouped = df.groupby(group_col, as_index=False).agg(islands_count=("nom", "count") if "nom" in df.columns else (group_col, "count"))
    grouped["islands_raw"] = grouped.iloc[:, 1]
    return grouped

def _load_islands_equipements_scores(iris: pd.DataFrame, group_col: str) -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "ilots-de-fraicheur-equipements-activites.parquet")
    if "longitude" in df.columns and "latitude" in df.columns:
        df = attach_iris_from_points(df, "longitude", "latitude", iris)
    else:
        df[group_col] = None
        
    df = df.dropna(subset=[group_col]).copy()
    grouped = df.groupby(group_col, as_index=False).agg(islands_equip_count=(group_col, "count"))
    grouped["islands_equip_raw"] = grouped["islands_equip_count"]
    return grouped

def _load_sanisettes_scores(iris: pd.DataFrame, group_col: str) -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "sanisettesparis.parquet")
    df = attach_iris_from_points(df, "longitude", "latitude", iris)
    grouped = df.groupby(group_col, as_index=False).agg(sanisettes_count=(group_col, "count"))
    grouped["sanisettes_raw"] = grouped["sanisettes_count"]
    return grouped

def _load_tourism_zones_scores(iris: pd.DataFrame, group_col: str) -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "zones-touristiques-internationales.parquet")
    df = attach_iris_from_points(df, "longitude", "latitude", iris)
    grouped = df.groupby(group_col, as_index=False).agg(zones_tourism=("name", "count"))
    grouped["zones_tourism_raw"] = grouped["zones_tourism"]
    return grouped

def _load_chantiers_scores(iris: pd.DataFrame, group_col: str) -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "chantiers-a-paris.parquet")
    df = attach_iris_from_points(df, "longitude", "latitude", iris)
    grouped = df.groupby(group_col, as_index=False).agg(chantiers_count=(group_col, "count"))
    grouped["chantiers_raw"] = grouped["chantiers_count"]
    return grouped

def _load_trafic_scores(iris: pd.DataFrame, group_col: str) -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "trafic.parquet")
    df = attach_iris_from_points(df, "longitude", "latitude", iris)
    # We only count "Pré-saturé", "Saturé", "Bloqué" as negative
    df_congested = df[df["etat_trafic"].isin(["Pré-saturé", "Saturé", "Bloqué"])]
    grouped = df_congested.groupby(group_col, as_index=False).agg(trafic_count=(group_col, "count"))
    grouped["trafic_raw"] = grouped["trafic_count"]
    return grouped

def build_score_df(iris: pd.DataFrame, group_col: str, base_df: pd.DataFrame) -> pd.DataFrame:
    trees = _load_trees_scores(iris, group_col)
    islands = _load_freshness_islands_scores(iris, group_col)
    islands_equip = _load_islands_equipements_scores(iris, group_col)
    sanisettes = _load_sanisettes_scores(iris, group_col)
    zones = _load_tourism_zones_scores(iris, group_col)
    chantiers = _load_chantiers_scores(iris, group_col)
    trafic = _load_trafic_scores(iris, group_col)

    score = base_df.copy()
    score = score.merge(trees, on=group_col, how="left")
    score = score.merge(islands, on=group_col, how="left")
    score = score.merge(islands_equip, on=group_col, how="left")
    score = score.merge(sanisettes, on=group_col, how="left")
    score = score.merge(zones, on=group_col, how="left")
    score = score.merge(chantiers, on=group_col, how="left")
    score = score.merge(trafic, on=group_col, how="left")

    numeric_columns = [
        "trees_count", "trees_raw",
        "islands_count", "islands_raw",
        "islands_equip_count", "islands_equip_raw",
        "sanisettes_count", "sanisettes_raw",
        "zones_tourism", "zones_tourism_raw",
        "chantiers_count", "chantiers_raw",
        "trafic_count", "trafic_raw",
    ]
    for column in numeric_columns:
        if column not in score.columns:
            score[column] = 0
        score[column] = score[column].fillna(0)

    score["trees_norm"] = _normalize_weights(score["trees_raw"]) 
    score["islands_norm"] = _normalize_weights(score["islands_raw"]) 
    score["islands_equip_norm"] = _normalize_weights(score["islands_equip_raw"]) 
    score["sanisettes_norm"] = _normalize_weights(score["sanisettes_raw"]) 
    score["zones_tourism_norm"] = _normalize_weights(score["zones_tourism_raw"]) 
    score["chantiers_norm"] = _normalize_weights(score["chantiers_raw"]) 
    score["trafic_norm"] = _normalize_weights(score["trafic_raw"]) 

    score["positive_score"] = (
        0.40 * score["trees_norm"]
        + 0.40 * score["islands_norm"]
        + 0.20 * score["islands_equip_norm"]
    )
    score["negative_score"] = 0.25 * score["sanisettes_norm"] + 0.25 * score["zones_tourism_norm"] + 0.25 * score["chantiers_norm"] + 0.25 * score["trafic_norm"]

    raw_final = score["positive_score"] - 0.2 * score["negative_score"]
    s_min = raw_final.min()
    s_max = raw_final.max()
    if s_max > s_min:
        score["score_qualite_environnement"] = (20 + 80 * (raw_final - s_min) / (s_max - s_min)).round(2)
    else:
        score["score_qualite_environnement"] = 50.0

    score = score.sort_values("score_qualite_environnement", ascending=False).reset_index(drop=True)
    return score

def build_gold_scores() -> tuple[pd.DataFrame, pd.DataFrame]:
    iris = load_paris_iris()
    
    # Arrondissement level
    arr_base = pd.DataFrame({"arrondissement": list(range(1, 21))})
    score_arr = build_score_df(iris, "arrondissement", arr_base)
    score_arr["arrondissement_libelle"] = score_arr["arrondissement"].apply(lambda value: f"Paris {int(value)}e Arrondissement")
    
    # IRIS level
    iris_base = iris[["code_iris", "nom_iris", "arrondissement", "nom_com"]].drop_duplicates()
    score_iris = build_score_df(iris, "code_iris", iris_base)
    
    return score_arr, score_iris

def main() -> None:
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    score_arr, score_iris = build_gold_scores()
    
    path_arr = GOLD_DIR / "score_qualite_de_vie.parquet"
    score_arr.to_parquet(path_arr, index=False)
    print(f"Ecrit: {path_arr}")
    
    path_iris = GOLD_DIR / "score_qualite_de_vie_iris.parquet"
    score_iris.to_parquet(path_iris, index=False)
    print(f"Ecrit: {path_iris}")

if __name__ == "__main__":
    main()
