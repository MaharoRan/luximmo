from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO_ROOT))

from utils.geo_helpers import load_paris_iris, attach_iris_from_points

SILVER_DIR = REPO_ROOT / "Indicateur_0" / "silver"
GOLD_DIR = REPO_ROOT / "Indicateur_0" / "gold"

def build_gold_scores() -> tuple[pd.DataFrame, pd.DataFrame]:
    files = list(SILVER_DIR.glob("paris_*.parquet"))
    if not files:
        raise FileNotFoundError(f"Aucun fichier parquet trouvé dans {SILVER_DIR}")
    
    dfs = []
    for file in files:
        df = pd.read_parquet(file)
        dfs.append(df)
        
    full_df = pd.concat(dfs, ignore_index=True)
    
    # Attach IRIS and Arrondissement based on lon/lat
    iris = load_paris_iris()
    full_df = attach_iris_from_points(full_df, "longitude", "latitude", iris)
    
    # --- ARRONDISSEMENT LEVEL ---
    grouped_arr = full_df.groupby("arrondissement")["valeur_fonciere"].agg(
        loyer_moyen="mean",
        loyer_median="median",
        loyer_minimum="min",
        loyer_maximum="max"
    ).reset_index()
    
    arrondissements_df = pd.DataFrame({"arrondissement": list(range(1, 21))})
    res_arr = arrondissements_df.merge(grouped_arr, on="arrondissement", how="left")
    
    # --- IRIS LEVEL ---
    grouped_iris = full_df.groupby("code_iris")["valeur_fonciere"].agg(
        loyer_moyen="mean",
        loyer_median="median",
        loyer_minimum="min",
        loyer_maximum="max"
    ).reset_index()
    
    iris_base = iris[["code_iris", "nom_iris", "arrondissement", "nom_com"]].drop_duplicates()
    res_iris = iris_base.merge(grouped_iris, on="code_iris", how="left")
    
    return res_arr, res_iris

def main() -> None:
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    score_arr, score_iris = build_gold_scores()
    
    path_arr = GOLD_DIR / "statistiques_loyer.parquet"
    score_arr.to_parquet(path_arr, index=False)
    print(f"Ecrit: {path_arr}")
    
    path_iris = GOLD_DIR / "statistiques_loyer_iris.parquet"
    score_iris.to_parquet(path_iris, index=False)
    print(f"Ecrit: {path_iris}")

if __name__ == "__main__":
    main()
