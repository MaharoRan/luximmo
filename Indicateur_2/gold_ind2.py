from __future__ import annotations

import re
import sys
from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO_ROOT))

from utils.geo_helpers import load_paris_iris, attach_iris_from_points, extract_paris_arrondissement

SILVER_DIR = REPO_ROOT / "Indicateur_2" / "silver"
GOLD_DIR = REPO_ROOT / "Indicateur_2" / "gold"

def _normalize_weights(series: pd.Series) -> pd.Series:
    maximum = series.max(skipna=True)
    if pd.isna(maximum) or maximum <= 0:
        return series * 0
    return series / maximum

def _keyword_score(text: str) -> float:
    return 1.0 if any(k in text for k in ["festival", "concert", "exposition", "soirée"]) else 0.0

def _score_event_weight(text: str) -> float:
    lowered = str(text).lower()
    if not lowered or lowered == "nan":
        return 0.0
    if re.search(r"\b(restaurant|bar|discoth[eé]que)\b", lowered):
        return 1.35
    if re.search(r"\b(mus[é]e|cin[é]ma|th[é]atre)\b", lowered):
        return 1.15
    return 0.25 if _keyword_score(lowered) > 0 else 0.0

def _load_activities_scores() -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "que-faire-a-paris.parquet")
    combined_text = df["title"].astype(str).fillna("") + " " + df["address_name"].astype(str).fillna("")
    df["arrondissement"] = combined_text.apply(extract_paris_arrondissement)
    df = df.dropna(subset=["arrondissement"]).copy()
    df["arrondissement"] = df["arrondissement"].astype(int)
    df["event_weight"] = combined_text.apply(_score_event_weight)

    grouped = df.groupby("arrondissement", as_index=False).agg(
        activities_count=("id", "count"),
        activities_weight=("event_weight", "sum"),
    )
    grouped["activities_raw"] = grouped["activities_count"] * 0.7 + grouped["activities_weight"]
    return grouped

def _load_voirie_activity_scores(iris: pd.DataFrame, group_col: str) -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "plan de voirie.parquet")
    df = attach_iris_from_points(df, "longitude", "latitude", iris)
    grouped = df.groupby(group_col, as_index=False).agg(voirie_activity_segments=(group_col, "count"))
    grouped["voirie_activity_raw"] = grouped["voirie_activity_segments"]
    return grouped

def _load_green_space_scores(iris: pd.DataFrame, group_col: str) -> pd.DataFrame:
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
        df[group_col] = None
    df = df.dropna(subset=[group_col]).copy()
    grouped = df.groupby(group_col, as_index=False).agg(islands_count=("nom", "count") if "nom" in df.columns else (group_col, "count"))
    grouped["islands_raw"] = grouped["islands_count"]
    return grouped

def _load_association_scores() -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "liste_des_associations_parisiennes.parquet")
    df["arrondissement"] = df["cp_adresse_code_postal"].apply(extract_paris_arrondissement)
    df = df.dropna(subset=["arrondissement"]).copy()
    df["arrondissement"] = df["arrondissement"].astype(int)
    grouped = df.groupby("arrondissement", as_index=False).agg(associations_count=("pr_nom_statutaire", "count"))
    grouped["associations_raw"] = grouped["associations_count"]
    return grouped

def _load_film_scores(iris: pd.DataFrame, group_col: str) -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "lieux-de-tournage-a-paris.parquet")
    if "longitude" in df.columns and "latitude" in df.columns:
        df = attach_iris_from_points(df, "longitude", "latitude", iris)
    else:
        df["arrondissement"] = df["ardt_lieu"].apply(extract_paris_arrondissement)
        if group_col == "code_iris":
            return pd.DataFrame({group_col: [], "film_locations": [], "film_raw": []})
        df = df.dropna(subset=["arrondissement"]).copy()
        df["arrondissement"] = df["arrondissement"].astype(int)
    grouped = df.groupby(group_col, as_index=False).agg(film_locations=(group_col, "count"))
    grouped["film_raw"] = grouped["film_locations"]
    return grouped

def _load_tourism_scores(iris: pd.DataFrame, group_col: str) -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "zones-touristiques-internationales.parquet")
    df = attach_iris_from_points(df, "longitude", "latitude", iris)
    grouped = df.groupby(group_col, as_index=False).agg(tourism_zones=("name", "count"))
    grouped["tourism_raw"] = grouped["tourism_zones"]
    return grouped

def build_score_df(iris: pd.DataFrame, group_col: str, base_df: pd.DataFrame) -> pd.DataFrame:
    activities = _load_activities_scores() # only arrondissement
    voirie = _load_voirie_activity_scores(iris, group_col)
    trees = _load_green_space_scores(iris, group_col)
    islands = _load_freshness_islands_scores(iris, group_col)
    associations = _load_association_scores() # only arrondissement
    films = _load_film_scores(iris, group_col)
    tourism = _load_tourism_scores(iris, group_col)

    score = base_df.copy()
    # Merge arrondissement level data if necessary
    score = score.merge(activities, on="arrondissement", how="left")
    score = score.merge(associations, on="arrondissement", how="left")
    
    # Merge grouped data
    score = score.merge(voirie, on=group_col, how="left")
    score = score.merge(trees, on=group_col, how="left")
    score = score.merge(islands, on=group_col, how="left")
    score = score.merge(films, on=group_col, how="left")
    score = score.merge(tourism, on=group_col, how="left")

    numeric_columns = [
        "activities_count", "activities_weight", "activities_raw",
        "voirie_activity_segments", "voirie_activity_raw",
        "trees_count", "trees_raw",
        "islands_count", "islands_raw",
        "associations_count", "associations_raw",
        "film_locations", "film_raw",
        "tourism_zones", "tourism_raw",
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

    raw_final = (
        0.60 * score["tourism_norm"]
        + 0.15 * score["activities_norm"]
        + 0.10 * score["voirie_activity_norm"]
        + 0.05 * score["film_norm"]
        + 0.05 * score["associations_norm"]
        + 0.03 * score["trees_norm"]
        + 0.02 * score["islands_norm"]
    )
    
    s_min = raw_final.min()
    s_max = raw_final.max()
    if s_max > s_min:
        score["score_interet_culturel_loisir"] = (20 + 80 * (raw_final - s_min) / (s_max - s_min)).round(2)
    else:
        score["score_interet_culturel_loisir"] = 50.0

    score = score.sort_values("score_interet_culturel_loisir", ascending=False).reset_index(drop=True)
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
    
    path_arr = GOLD_DIR / "score_interet_culturel_loisir.parquet"
    score_arr.to_parquet(path_arr, index=False)
    print(f"Ecrit: {path_arr}")
    
    path_iris = GOLD_DIR / "score_interet_culturel_loisir_iris.parquet"
    score_iris.to_parquet(path_iris, index=False)
    print(f"Ecrit: {path_iris}")

if __name__ == "__main__":
    main()
