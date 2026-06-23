from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO_ROOT))

from utils.geo_helpers import load_paris_iris, attach_iris_from_points

SILVER_DIR = REPO_ROOT / "Indicateur_0" / "silver"
GOLD_DIR = REPO_ROOT / "Indicateur_0" / "gold"


def _prepare_dvf() -> pd.DataFrame:
    files = list(SILVER_DIR.glob("paris_*.parquet"))

    if not files:
        raise FileNotFoundError(f"Aucun fichier parquet trouvé dans {SILVER_DIR}")

    dfs = [pd.read_parquet(file) for file in files]
    full_df = pd.concat(dfs, ignore_index=True)

    full_df["date_mutation"] = pd.to_datetime(full_df["date_mutation"], errors="coerce")
    full_df["year"] = full_df["date_mutation"].dt.year

    full_df["valeur_fonciere"] = pd.to_numeric(full_df["valeur_fonciere"], errors="coerce")
    full_df["surface_reelle_bati"] = pd.to_numeric(full_df["surface_reelle_bati"], errors="coerce")
    full_df["longitude"] = pd.to_numeric(full_df["longitude"], errors="coerce")
    full_df["latitude"] = pd.to_numeric(full_df["latitude"], errors="coerce")

    full_df["arrondissement"] = full_df["code_postal"].astype(str).str[-2:].astype(int)
    full_df["prix_m2"] = full_df["valeur_fonciere"] / full_df["surface_reelle_bati"]

    full_df = full_df.dropna(
        subset=["prix_m2", "year", "arrondissement", "longitude", "latitude"]
    ).copy()

    full_df = full_df[
        (full_df["prix_m2"] >= 1000)
        & (full_df["prix_m2"] <= 30000)
    ].copy()

    return full_df


def build_gold_scores() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    full_df = _prepare_dvf()

    grouped_year = full_df.groupby(["arrondissement", "year"]).agg(
        prix_m2_median=("prix_m2", "median"),
        prix_m2_mean=("prix_m2", "mean"),
        valeur_fonciere_median=("valeur_fonciere", "median"),
        surface_median=("surface_reelle_bati", "median"),
        transactions_count=("prix_m2", "count"),
    ).reset_index()

    grouped_year["prix_m2_median"] = grouped_year["prix_m2_median"].round(0)
    grouped_year["prix_m2_mean"] = grouped_year["prix_m2_mean"].round(0)
    grouped_year["valeur_fonciere_median"] = grouped_year["valeur_fonciere_median"].round(0)
    grouped_year["surface_median"] = grouped_year["surface_median"].round(1)

    grouped_arr = full_df.groupby("arrondissement").agg(
        loyer_moyen=("prix_m2", "mean"),
        loyer_median=("prix_m2", "median"),
        loyer_minimum=("prix_m2", "min"),
        loyer_maximum=("prix_m2", "max"),
    ).reset_index()

    grouped_arr[["loyer_moyen", "loyer_median", "loyer_minimum", "loyer_maximum"]] = (
        grouped_arr[["loyer_moyen", "loyer_median", "loyer_minimum", "loyer_maximum"]].round(0)
    )

    arrondissements_df = pd.DataFrame({"arrondissement": list(range(1, 21))})
    result_arr = arrondissements_df.merge(grouped_arr, on="arrondissement", how="left")

    iris = load_paris_iris()
    iris_df = attach_iris_from_points(full_df, "longitude", "latitude", iris)

    grouped_iris = iris_df.groupby("code_iris").agg(
        loyer_moyen=("prix_m2", "mean"),
        loyer_median=("prix_m2", "median"),
        loyer_minimum=("prix_m2", "min"),
        loyer_maximum=("prix_m2", "max"),
    ).reset_index()

    grouped_iris[["loyer_moyen", "loyer_median", "loyer_minimum", "loyer_maximum"]] = (
        grouped_iris[["loyer_moyen", "loyer_median", "loyer_minimum", "loyer_maximum"]].round(0)
    )

    iris_base = iris[["code_iris", "nom_iris", "arrondissement", "nom_com"]].drop_duplicates()
    result_iris = iris_base.merge(grouped_iris, on="code_iris", how="left")

    return grouped_year.sort_values(["year", "arrondissement"]), result_arr, result_iris


def main() -> None:
    GOLD_DIR.mkdir(parents=True, exist_ok=True)

    score_year, score_arr, score_iris = build_gold_scores()

    path_year = GOLD_DIR / "prix_m2_arrondissement_year.parquet"
    score_year.to_parquet(path_year, index=False)
    print(f"Ecrit: {path_year}")

    path_arr = GOLD_DIR / "statistiques_loyer.parquet"
    score_arr.to_parquet(path_arr, index=False)
    print(f"Ecrit: {path_arr}")

    path_iris = GOLD_DIR / "statistiques_loyer_iris.parquet"
    score_iris.to_parquet(path_iris, index=False)
    print(f"Ecrit: {path_iris}")


if __name__ == "__main__":
    main()