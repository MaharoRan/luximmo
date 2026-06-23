from pathlib import Path

import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parents[1]

app = FastAPI(title="LuxImmo API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_gold_scores():
    """Charge les 4 indicateurs avec TOUTES leurs colonnes détaillées."""
    ind1 = pd.read_parquet(
        ROOT / "Indicateur_1" / "gold" / "score_qualite_de_vie.parquet"
    ).drop(columns=["arrondissement_libelle"], errors="ignore")

    ind2 = pd.read_parquet(
        ROOT / "Indicateur_2" / "gold" / "score_interet_culturel_loisir.parquet"
    ).drop(columns=["arrondissement_libelle"], errors="ignore")

    ind3 = pd.read_parquet(
        ROOT / "Indicateur_3" / "gold" / "score_acces_services_publiques.parquet"
    ).drop(columns=["arrondissement_libelle"], errors="ignore")

    ind4 = pd.read_parquet(
        ROOT / "Indicateur_4" / "gold" / "score_acces_transport.parquet"
    ).drop(columns=["arrondissement_libelle"], errors="ignore")

    # Renommer les scores principaux
    ind1 = ind1.rename(columns={"score_qualite_environnement": "quality"})
    ind2 = ind2.rename(columns={"score_interet_culturel_loisir": "culture"})
    ind3 = ind3.rename(columns={"score_acces_services_publiques": "services"})
    ind4 = ind4.rename(columns={"score_acces_transport": "transport"})

    # Préfixer les colonnes détaillées pour éviter les collisions (trees_count existe dans ind1 et ind2)
    detail_rename_1 = {}
    detail_rename_2 = {}
    for col in ind1.columns:
        if col not in ("arrondissement", "quality"):
            detail_rename_1[col] = f"q_{col}"
    for col in ind2.columns:
        if col not in ("arrondissement", "culture"):
            detail_rename_2[col] = f"c_{col}"

    ind1 = ind1.rename(columns=detail_rename_1)
    ind2 = ind2.rename(columns=detail_rename_2)

    # ind3 et ind4 n'ont pas de collisions entre eux
    detail_rename_3 = {}
    for col in ind3.columns:
        if col not in ("arrondissement", "services"):
            detail_rename_3[col] = f"s_{col}"
    ind3 = ind3.rename(columns=detail_rename_3)

    detail_rename_4 = {}
    for col in ind4.columns:
        if col not in ("arrondissement", "transport"):
            detail_rename_4[col] = f"t_{col}"
    ind4 = ind4.rename(columns=detail_rename_4)

    scores = ind1.merge(ind2, on="arrondissement", how="outer")
    scores = scores.merge(ind3, on="arrondissement", how="outer")
    scores = scores.merge(ind4, on="arrondissement", how="outer")

    return scores


def load_prix():
    prix = pd.read_parquet(
        ROOT / "Indicateur_0" / "gold" / "statistiques_loyer.parquet"
    )
    return prix[["arrondissement", "loyer_moyen", "loyer_median", "loyer_maximum"]]


def load_gold_scores_iris():
    """Charge les 4 indicateurs à l'échelle de l'IRIS avec TOUTES leurs colonnes détaillées."""
    ind1 = pd.read_parquet(ROOT / "Indicateur_1" / "gold" / "score_qualite_de_vie_iris.parquet").drop(columns=["arrondissement_libelle"], errors="ignore")
    ind2 = pd.read_parquet(ROOT / "Indicateur_2" / "gold" / "score_interet_culturel_loisir_iris.parquet").drop(columns=["arrondissement_libelle"], errors="ignore")
    ind3 = pd.read_parquet(ROOT / "Indicateur_3" / "gold" / "score_acces_services_publiques_iris.parquet").drop(columns=["arrondissement_libelle"], errors="ignore")
    ind4 = pd.read_parquet(ROOT / "Indicateur_4" / "gold" / "score_acces_transport_iris.parquet").drop(columns=["arrondissement_libelle"], errors="ignore")

    ind1 = ind1.rename(columns={"score_qualite_environnement": "quality"})
    ind2 = ind2.rename(columns={"score_interet_culturel_loisir": "culture"})
    ind3 = ind3.rename(columns={"score_acces_services_publiques": "services"})
    ind4 = ind4.rename(columns={"score_acces_transport": "transport"})

    detail_rename_1 = {col: f"q_{col}" for col in ind1.columns if col not in ("code_iris", "nom_iris", "nom_com", "arrondissement", "quality")}
    detail_rename_2 = {col: f"c_{col}" for col in ind2.columns if col not in ("code_iris", "nom_iris", "nom_com", "arrondissement", "culture")}
    detail_rename_3 = {col: f"s_{col}" for col in ind3.columns if col not in ("code_iris", "nom_iris", "nom_com", "arrondissement", "services")}
    detail_rename_4 = {col: f"t_{col}" for col in ind4.columns if col not in ("code_iris", "nom_iris", "nom_com", "arrondissement", "transport")}

    ind1 = ind1.rename(columns=detail_rename_1)
    ind2 = ind2.rename(columns=detail_rename_2)
    ind3 = ind3.rename(columns=detail_rename_3)
    ind4 = ind4.rename(columns=detail_rename_4)

    scores = ind1.merge(ind2, on=["code_iris", "nom_iris", "arrondissement", "nom_com"], how="outer")
    scores = scores.merge(ind3, on=["code_iris", "nom_iris", "arrondissement", "nom_com"], how="outer")
    scores = scores.merge(ind4, on=["code_iris", "nom_iris", "arrondissement", "nom_com"], how="outer")

    return scores


def load_prix_iris():
    prix = pd.read_parquet(ROOT / "Indicateur_0" / "gold" / "statistiques_loyer_iris.parquet")
    return prix[["code_iris", "loyer_moyen", "loyer_median", "loyer_maximum"]]


@app.get("/")
def root():
    return {"message": "LuxImmo API is running"}

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/arrondissements")
def get_arrondissements():
    """Retourne les données agrégées par arrondissement : scores détaillés + prix."""
    scores = load_gold_scores()
    prix = load_prix()

    result = scores.merge(prix, on="arrondissement", how="outer")

    # S'assurer que tous les arrondissements 1-20 sont présents
    all_arr = pd.DataFrame({"arrondissement": list(range(1, 21))})
    result = all_arr.merge(result, on="arrondissement", how="left")

    result[["quality", "culture", "services", "transport"]] = result[
        ["quality", "culture", "services", "transport"]
    ].fillna(50)

    result[["loyer_moyen", "loyer_median", "loyer_maximum"]] = result[
        ["loyer_moyen", "loyer_median", "loyer_maximum"]
    ].fillna(0)

    # Normaliser le prix median en score 0-100 (inversé : cher = bas score = rouge)
    median_min = result["loyer_median"].min()
    median_max = result["loyer_median"].max()
    if median_max > median_min:
        result["prix_score"] = (
            100 - ((result["loyer_median"] - median_min) / (median_max - median_min) * 100)
        ).round(1)
    else:
        result["prix_score"] = 50.0

    # Remplir les NaN restants avec 0
    result = result.fillna(0)

    return result.to_dict(orient="records")


@app.get("/api/iris")
def get_iris():
    """Retourne les données agrégées par IRIS : scores détaillés + prix."""
    scores = load_gold_scores_iris()
    prix = load_prix_iris()

    result = scores.merge(prix, on="code_iris", how="left")

    result[["quality", "culture", "services", "transport"]] = result[
        ["quality", "culture", "services", "transport"]
    ].fillna(50)

    result[["loyer_moyen", "loyer_median", "loyer_maximum"]] = result[
        ["loyer_moyen", "loyer_median", "loyer_maximum"]
    ].fillna(0)

    # Normaliser le prix median en score 0-100 (inversé : cher = bas score = rouge)
    # Ignorer les zéros pour trouver le minimum
    valid_medians = result[result["loyer_median"] > 0]["loyer_median"]
    median_min = valid_medians.min() if not valid_medians.empty else 0
    median_max = result["loyer_median"].max()
    
    if pd.notna(median_max) and pd.notna(median_min) and median_max > median_min:
        result["prix_score"] = result.apply(
            lambda row: 50.0 if row["loyer_median"] == 0 else (100 - ((row["loyer_median"] - median_min) / (median_max - median_min) * 100)),
            axis=1
        ).round(1)
    else:
        result["prix_score"] = 50.0

    # Remplir les NaN restants avec 0
    result = result.fillna(0)

    return result.to_dict(orient="records")