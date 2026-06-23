from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import itertools

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(REPO_ROOT))

from utils.geo_helpers import load_paris_iris, attach_iris_from_points

SILVER_DIR = REPO_ROOT / "Indicateur_0" / "silver"
GOLD_DIR = REPO_ROOT / "Indicateur_0" / "gold"

<<<<<<< Updated upstream

def _prepare_dvf() -> pd.DataFrame:
=======
TARGET_YEARS = [2021, 2022, 2023, 2024, 2025]

def build_gold_scores() -> tuple[pd.DataFrame, pd.DataFrame]:
>>>>>>> Stashed changes
    files = list(SILVER_DIR.glob("paris_*.parquet"))

    if not files:
        raise FileNotFoundError(f"Aucun fichier parquet trouvé dans {SILVER_DIR}")

    dfs = [pd.read_parquet(file) for file in files]
    full_df = pd.concat(dfs, ignore_index=True)
<<<<<<< Updated upstream

    full_df["date_mutation"] = pd.to_datetime(full_df["date_mutation"], errors="coerce")
    full_df["year"] = full_df["date_mutation"].dt.year

    full_df["valeur_fonciere"] = pd.to_numeric(full_df["valeur_fonciere"], errors="coerce")
    full_df["surface_reelle_bati"] = pd.to_numeric(full_df["surface_reelle_bati"], errors="coerce")
    full_df["longitude"] = pd.to_numeric(full_df["longitude"], errors="coerce")
    full_df["latitude"] = pd.to_numeric(full_df["latitude"], errors="coerce")

    full_df["arrondissement"] = full_df["code_postal"].astype(str).str[-2:].astype(int)

    # Grouper par mutation
    if "id_mutation" in full_df.columns:
        mutation_df = full_df.groupby("id_mutation").agg(
            valeur_fonciere=("valeur_fonciere", "max"),
            surface_reelle_bati=("surface_reelle_bati", "sum"),
            year=("year", "first"),
            arrondissement=("arrondissement", "first"),
            longitude=("longitude", "first"),
            latitude=("latitude", "first")
        ).reset_index()
    else:
        mutation_df = full_df

    # Calcul du prix au m2
    mutation_df["prix_m2"] = mutation_df["valeur_fonciere"] / mutation_df["surface_reelle_bati"]

    mutation_df = mutation_df.dropna(
        subset=["prix_m2", "year", "arrondissement", "longitude", "latitude"]
    ).copy()

    # Filtrer les valeurs aberrantes
    mutation_df = mutation_df[
        (mutation_df["prix_m2"] >= 1000)
        & (mutation_df["prix_m2"] <= 30000)
    ].copy()

    return mutation_df


def _agg_scores(df: pd.DataFrame, groupby_cols: str | list[str]) -> pd.DataFrame:
    agg_df = df.groupby(groupby_cols).agg(
        prix_vente_moyen=("valeur_fonciere", "mean"),
        prix_vente_median=("valeur_fonciere", "median"),
        surface_moyenne=("surface_reelle_bati", "mean"),
        surface_mediane=("surface_reelle_bati", "median"),
        surface_maximum=("surface_reelle_bati", "max"),
        prix_m2_moyen=("prix_m2", "mean"),
        prix_m2_median=("prix_m2", "median"),
        prix_m2_minimum=("prix_m2", "min"),
        prix_m2_maximum=("prix_m2", "max"),
        transactions_count=("prix_m2", "count"),
    ).reset_index()

    cols_to_round = [
        "prix_vente_moyen", "prix_vente_median", 
        "surface_moyenne", "surface_mediane", "surface_maximum",
        "prix_m2_moyen", "prix_m2_median", "prix_m2_minimum", "prix_m2_maximum"
    ]
    agg_df[cols_to_round] = agg_df[cols_to_round].round(0)
    return agg_df


def build_gold_scores() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    full_df = _prepare_dvf()

    # ARRONDISSEMENT + YEAR
    arr_year = _agg_scores(full_df, ["arrondissement", "year"])

    # ARRONDISSEMENT GLOBAL
    arr_global = _agg_scores(full_df, ["arrondissement"])
    arrondissements_df = pd.DataFrame({"arrondissement": list(range(1, 21))})
    arr_global = arrondissements_df.merge(arr_global, on="arrondissement", how="left")

    # IRIS
    iris = load_paris_iris()
    iris_df = attach_iris_from_points(full_df, "longitude", "latitude", iris)
    iris_base = iris[["code_iris", "nom_iris", "arrondissement", "nom_com"]].drop_duplicates()

    # IRIS GLOBAL
    iris_global = _agg_scores(iris_df, ["code_iris"])
    iris_global = iris_base.merge(iris_global, on="code_iris", how="left")

    # IRIS + YEAR
    iris_year = _agg_scores(iris_df, ["code_iris", "year"])
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
=======
    
    # Cross join IRIS with Years
    iris_years = pd.merge(iris_base.assign(key=1), pd.DataFrame({"year": TARGET_YEARS, "key": 1}), on="key").drop("key", axis=1)
    res_iris = iris_years.merge(grouped_iris, on=["code_iris", "year"], how="left")
    
    return res_arr, res_iris

def main() -> None:
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    score_arr, score_iris = build_gold_scores()
    
    path_arr = GOLD_DIR / "statistiques_loyer_annee.parquet"
    score_arr.to_parquet(path_arr, index=False)
    print(f"Ecrit: {path_arr}")
    
    path_iris = GOLD_DIR / "statistiques_loyer_iris_annee.parquet"
    score_iris.to_parquet(path_iris, index=False)
>>>>>>> Stashed changes
    print(f"Ecrit: {path_iris}")

    path_iris_year = GOLD_DIR / "statistiques_loyer_iris_year.parquet"
    iris_year.to_parquet(path_iris_year, index=False)
    print(f"Ecrit: {path_iris_year}")


if __name__ == "__main__":
    main()