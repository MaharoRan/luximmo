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


def build_gold_scores() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    full_df = _prepare_dvf()

    # ARRONDISSEMENT + YEAR
    arr_year = full_df.groupby(["arrondissement", "year"]).agg(
        prix_m2_median=("prix_m2", "median"),
        prix_m2_mean=("prix_m2", "mean"),
        valeur_fonciere_median=("valeur_fonciere", "median"),
        surface_median=("surface_reelle_bati", "median"),
        transactions_count=("prix_m2", "count"),
    ).reset_index()

    arr_year["prix_m2_median"] = arr_year["prix_m2_median"].round(0)
    arr_year["prix_m2_mean"] = arr_year["prix_m2_mean"].round(0)
    arr_year["valeur_fonciere_median"] = arr_year["valeur_fonciere_median"].round(0)
    arr_year["surface_median"] = arr_year["surface_median"].round(1)

    # ARRONDISSEMENT GLOBAL
    arr_global = full_df.groupby("arrondissement").agg(
        loyer_moyen=("prix_m2", "mean"),
        loyer_median=("prix_m2", "median"),
        loyer_minimum=("prix_m2", "min"),
        loyer_maximum=("prix_m2", "max"),
    ).reset_index()

    arr_global[["loyer_moyen", "loyer_median", "loyer_minimum", "loyer_maximum"]] = (
        arr_global[["loyer_moyen", "loyer_median", "loyer_minimum", "loyer_maximum"]].round(0)
    )

    arrondissements_df = pd.DataFrame({"arrondissement": list(range(1, 21))})
    arr_global = arrondissements_df.merge(arr_global, on="arrondissement", how="left")

    # IRIS
    iris = load_paris_iris()
    iris_df = attach_iris_from_points(full_df, "longitude", "latitude", iris)

    # IRIS GLOBAL
    iris_global = iris_df.groupby("code_iris").agg(
        loyer_moyen=("prix_m2", "mean"),
        loyer_median=("prix_m2", "median"),
        loyer_minimum=("prix_m2", "min"),
        loyer_maximum=("prix_m2", "max"),
    ).reset_index()

    iris_global[["loyer_moyen", "loyer_median", "loyer_minimum", "loyer_maximum"]] = (
        iris_global[["loyer_moyen", "loyer_median", "loyer_minimum", "loyer_maximum"]].round(0)
    )

    iris_base = iris[["code_iris", "nom_iris", "arrondissement", "nom_com"]].drop_duplicates()
    iris_global = iris_base.merge(iris_global, on="code_iris", how="left")

    # IRIS + YEAR
    iris_year = iris_df.groupby(["code_iris", "year"]).agg(
        loyer_moyen=("prix_m2", "mean"),
        loyer_median=("prix_m2", "median"),
        loyer_minimum=("prix_m2", "min"),
        loyer_maximum=("prix_m2", "max"),
        transactions_count=("prix_m2", "count"),
    ).reset_index()

    iris_year[["loyer_moyen", "loyer_median", "loyer_minimum", "loyer_maximum"]] = (
        iris_year[["loyer_moyen", "loyer_median", "loyer_minimum", "loyer_maximum"]].round(0)
    )

    iris_year = iris_base.merge(iris_year, on="code_iris", how="left")

    return (
        arr_year.sort_values(["year", "arrondissement"]),
        arr_global,
        iris_global,
        iris_year.sort_values(["year", "code_iris"]),
    )


def main() -> None:
    GOLD_DIR.mkdir(parents=True, exist_ok=True)

    arr_year, arr_global, iris_global, iris_year = build_gold_scores()

    path_arr_year = GOLD_DIR / "prix_m2_arrondissement_year.parquet"
    arr_year.to_parquet(path_arr_year, index=False)
    print(f"Ecrit: {path_arr_year}")

    path_arr = GOLD_DIR / "statistiques_loyer.parquet"
    arr_global.to_parquet(path_arr, index=False)
    print(f"Ecrit: {path_arr}")

    path_iris = GOLD_DIR / "statistiques_loyer_iris.parquet"
    iris_global.to_parquet(path_iris, index=False)
    print(f"Ecrit: {path_iris}")

    path_iris_year = GOLD_DIR / "statistiques_loyer_iris_year.parquet"
    iris_year.to_parquet(path_iris_year, index=False)
    print(f"Ecrit: {path_iris_year}")


if __name__ == "__main__":
    main()