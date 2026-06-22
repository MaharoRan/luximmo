from __future__ import annotations

from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SILVER_DIR = REPO_ROOT / "Indicateur_0" / "silver"
GOLD_DIR = REPO_ROOT / "Indicateur_0" / "gold"

def build_gold_score() -> pd.DataFrame:
    # Gather all parquet files in silver dir
    files = list(SILVER_DIR.glob("paris_*.parquet"))
    if not files:
        raise FileNotFoundError(f"Aucun fichier parquet trouvé dans {SILVER_DIR}")
    
    dfs = []
    for file in files:
        df = pd.read_parquet(file)
        dfs.append(df)
        
    full_df = pd.concat(dfs, ignore_index=True)
    
    # Extract arrondissement from code_postal
    # code_postal is string "75001" etc., we want int 1-20
    full_df["arrondissement"] = full_df["code_postal"].astype(str).str[-2:].astype(int)
    
    # Calculate stats
    grouped = full_df.groupby("arrondissement")["valeur_fonciere"].agg(
        loyer_moyen="mean",
        loyer_median="median",
        loyer_minimum="min",
        loyer_maximum="max"
    ).reset_index()
    
    # Ensure all arrondissements are present
    arrondissements_df = pd.DataFrame({"arrondissement": list(range(1, 21))})
    result = arrondissements_df.merge(grouped, on="arrondissement", how="left")
    
    return result

def main() -> None:
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    score = build_gold_score()
    output_path = GOLD_DIR / "statistiques_loyer.parquet"
    score.to_parquet(output_path, index=False)
    print(f"Ecrit: {output_path}")

if __name__ == "__main__":
    main()
