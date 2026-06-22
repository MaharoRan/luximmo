from __future__ import annotations

from pathlib import Path
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
SILVER_DIR = REPO_ROOT / "Indicateur_0" / "silver"
GOLD_DIR = REPO_ROOT / "Indicateur_0" / "gold"


def build_gold_score() -> pd.DataFrame:
    files = list(SILVER_DIR.glob("paris_*.parquet"))

    if not files:
        raise FileNotFoundError(f"Aucun fichier parquet trouvé dans {SILVER_DIR}")

    dfs = [pd.read_parquet(file) for file in files]
    full_df = pd.concat(dfs, ignore_index=True)

    full_df["date_mutation"] = pd.to_datetime(full_df["date_mutation"], errors="coerce")
    full_df["year"] = full_df["date_mutation"].dt.year

    full_df["arrondissement"] = (
        full_df["code_postal"].astype(str).str[-2:].astype(int)
    )

    full_df["prix_m2"] = (
        full_df["valeur_fonciere"] / full_df["surface_reelle_bati"]
    )

    full_df = full_df.dropna(subset=["prix_m2", "year", "arrondissement"]).copy()

    # Filtre anti-valeurs absurdes
    full_df = full_df[
        (full_df["prix_m2"] >= 1000)
        & (full_df["prix_m2"] <= 30000)
    ].copy()

    grouped = full_df.groupby(["arrondissement", "year"]).agg(
        prix_m2_median=("prix_m2", "median"),
        prix_m2_mean=("prix_m2", "mean"),
        valeur_fonciere_median=("valeur_fonciere", "median"),
        surface_median=("surface_reelle_bati", "median"),
        transactions_count=("prix_m2", "count"),
    ).reset_index()

    grouped["prix_m2_median"] = grouped["prix_m2_median"].round(0)
    grouped["prix_m2_mean"] = grouped["prix_m2_mean"].round(0)
    grouped["valeur_fonciere_median"] = grouped["valeur_fonciere_median"].round(0)
    grouped["surface_median"] = grouped["surface_median"].round(1)

    return grouped.sort_values(["year", "arrondissement"])


def main() -> None:
    GOLD_DIR.mkdir(parents=True, exist_ok=True)

    score = build_gold_score()
    output_path = GOLD_DIR / "prix_m2_arrondissement_year.parquet"

    score.to_parquet(output_path, index=False)
    print(f"Ecrit: {output_path}")


if __name__ == "__main__":
    main()