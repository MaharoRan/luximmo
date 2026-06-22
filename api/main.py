from pathlib import Path

import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ROOT = Path(__file__).resolve().parents[1]

app = FastAPI(title="LuxImmo API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_paris_iris():
    iris_path = ROOT / "geo" / "iris.parquet"
    iris = pd.read_parquet(iris_path)

    iris = iris[
        iris["nom_com"].astype(str).str.contains("Paris", case=False, na=False)
    ].copy()

    iris["arrondissement"] = (
        iris["nom_com"]
        .astype(str)
        .str.extract(r"Paris\s+(\d{1,2})e\s+Arrondissement", expand=False)
    )

    iris = iris.dropna(subset=["arrondissement"]).copy()
    iris["arrondissement"] = iris["arrondissement"].astype(int)

    return iris[["code_iris", "nom_iris", "nom_com", "arrondissement"]]


def load_gold_scores():
    ind1 = pd.read_parquet(
        ROOT / "Indicateur_1" / "gold" / "score_qualite_de_vie.parquet"
    )[["arrondissement", "score_qualite_environnement"]]

    ind2 = pd.read_parquet(
        ROOT / "Indicateur_2" / "gold" / "score_interet_culturel_loisir.parquet"
    )[["arrondissement", "score_interet_culturel_loisir"]]

    ind3 = pd.read_parquet(
        ROOT / "Indicateur_3" / "gold" / "score_acces_services_publiques.parquet"
    )[["arrondissement", "score_acces_services_publiques"]]

    ind4 = pd.read_parquet(
        ROOT / "Indicateur_4" / "gold" / "score_acces_transport.parquet"
    )[["arrondissement", "score_acces_transport"]]

    scores = ind1.merge(ind2, on="arrondissement", how="outer")
    scores = scores.merge(ind3, on="arrondissement", how="outer")
    scores = scores.merge(ind4, on="arrondissement", how="outer")

    scores = scores.rename(
        columns={
            "score_qualite_environnement": "quality",
            "score_interet_culturel_loisir": "culture",
            "score_acces_services_publiques": "services",
            "score_acces_transport": "transport",
        }
    )

    return scores


def load_prices():
    prices_path = ROOT / "Indicateur_0" / "gold" / "prix_m2_arrondissement_year.parquet"
    prices = pd.read_parquet(prices_path)

    latest_year = int(prices["year"].max())

    latest_prices = prices[prices["year"] == latest_year].copy()

    return latest_prices[
        [
            "arrondissement",
            "year",
            "prix_m2_median",
            "prix_m2_mean",
            "valeur_fonciere_median",
            "surface_median",
            "transactions_count",
        ]
    ]


@app.get("/")
def root():
    return {"message": "LuxImmo API is running"}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/scores")
def get_scores():
    iris = load_paris_iris()
    scores = load_gold_scores()
    prices = load_prices()

    result = iris.merge(scores, on="arrondissement", how="left")
    result = result.merge(prices, on="arrondissement", how="left")

    result[["quality", "culture", "services", "transport"]] = result[
        ["quality", "culture", "services", "transport"]
    ].fillna(50)

    price_columns = [
        "prix_m2_median",
        "prix_m2_mean",
        "valeur_fonciere_median",
        "surface_median",
        "transactions_count",
    ]

    result[price_columns] = result[price_columns].fillna(0)

    return result[
        [
            "code_iris",
            "nom_iris",
            "nom_com",
            "arrondissement",
            "quality",
            "culture",
            "services",
            "transport",
            "year",
            "prix_m2_median",
            "prix_m2_mean",
            "valeur_fonciere_median",
            "surface_median",
            "transactions_count",
        ]
    ].to_dict(orient="records")