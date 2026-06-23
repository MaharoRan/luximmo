from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd
from shapely import wkb

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO_ROOT))

from utils.geo_helpers import load_paris_iris, attach_iris_from_points, extract_paris_arrondissement, safe_numeric_series

SILVER_DIR = REPO_ROOT / "Indicateur_4" / "silver"
GOLD_DIR = REPO_ROOT / "Indicateur_4" / "gold"

def _normalize_weights(series: pd.Series) -> pd.Series:
    maximum = series.max(skipna=True)
    if pd.isna(maximum) or maximum <= 0:
        return series * 0
    return series / maximum

def _load_gare_scores(iris: pd.DataFrame, group_col: str) -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "emplacement-des-gares-idf.parquet")
    df = attach_iris_from_points(df, "longitude", "latitude", iris)
    grouped = df.groupby(group_col, as_index=False).agg(gare_stations=("gares_id", "count"))
    grouped["gare_raw"] = grouped["gare_stations"]
    return grouped

def _load_velib_scores(iris: pd.DataFrame, group_col: str) -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "velib-emplacement-des-stations.parquet")
    if "coordonnees_geo" in df.columns:
        points = df["coordonnees_geo"].apply(lambda value: wkb.loads(value) if pd.notna(value) else None)
        df["longitude"] = points.apply(lambda geom: geom.x if geom is not None else None)
        df["latitude"] = points.apply(lambda geom: geom.y if geom is not None else None)
    
    df = attach_iris_from_points(df, "longitude", "latitude", iris)
    if "capacity" in df.columns:
        df["capacity"] = safe_numeric_series(df["capacity"]).fillna(0)
    else:
        df["capacity"] = 0

    grouped = df.groupby(group_col, as_index=False).agg(
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
    df["arrondissement"] = df["arrondissement"].apply(extract_paris_arrondissement)
    df = df.dropna(subset=["arrondissement"]).copy()
    df["arrondissement"] = df["arrondissement"].astype(int)
    df["cycling_weight"] = df.apply(lambda row: _amenagement_weight(row.get("amenagement"), row.get("coronapiste")), axis=1)

    grouped = df.groupby("arrondissement", as_index=False).agg(
        cycling_segments=("osm_id", "count"),
        cycling_weight=("cycling_weight", "sum"),
    )
    grouped["cycling_raw"] = grouped["cycling_weight"]
    return grouped

def _load_transport_proxy_scores(iris: pd.DataFrame, group_col: str) -> pd.DataFrame:
    df = pd.read_parquet(SILVER_DIR / "plan de voirie.parquet")
    df = attach_iris_from_points(df, "longitude", "latitude", iris)
    grouped = df.groupby(group_col, as_index=False).agg(transport_segments=(group_col, "count"))
    grouped["transport_raw"] = grouped["transport_segments"]
    return grouped

def build_score_df(iris: pd.DataFrame, group_col: str, base_df: pd.DataFrame) -> pd.DataFrame:
    gare = _load_gare_scores(iris, group_col)
    velib = _load_velib_scores(iris, group_col)
    cycling = _load_cycling_scores()
    transport = _load_transport_proxy_scores(iris, group_col)

    score = base_df.copy()
    score = score.merge(gare, on=group_col, how="left")
    score = score.merge(velib, on=group_col, how="left")
    score = score.merge(cycling, on="arrondissement", how="left")
    score = score.merge(transport, on=group_col, how="left")

    numeric_columns = [
        "gare_stations", "gare_raw",
        "velib_stations", "velib_capacity", "velib_raw",
        "cycling_segments", "cycling_weight", "cycling_raw",
        "transport_segments", "transport_raw",
    ]
    for column in numeric_columns:
        if column not in score.columns:
            score[column] = 0
        score[column] = score[column].fillna(0)

    score["gare_norm"] = _normalize_weights(score["gare_raw"])
    score["velib_norm"] = _normalize_weights(score["velib_raw"])
    score["cycling_norm"] = _normalize_weights(score["cycling_raw"])
    score["transport_norm"] = _normalize_weights(score["transport_raw"])

    raw_final = (
        0.45 * score["gare_norm"]
        + 0.30 * score["transport_norm"]
        + 0.15 * score["velib_norm"]
        + 0.10 * score["cycling_norm"]
    )
    
    s_min = raw_final.min()
    s_max = raw_final.max()
    if s_max > s_min:
        score["score_acces_transport"] = (20 + 80 * (raw_final - s_min) / (s_max - s_min)).round(2)
    else:
        score["score_acces_transport"] = 50.0

    score = score.sort_values("score_acces_transport", ascending=False).reset_index(drop=True)
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
    
    path_arr = GOLD_DIR / "score_acces_transport.parquet"
    score_arr.to_parquet(path_arr, index=False)
    print(f"Ecrit: {path_arr}")
    
    path_iris = GOLD_DIR / "score_acces_transport_iris.parquet"
    score_iris.to_parquet(path_iris, index=False)
    print(f"Ecrit: {path_iris}")

if __name__ == "__main__":
    main()