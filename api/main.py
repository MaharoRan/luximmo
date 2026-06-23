from pathlib import Path

import pandas as pd
from fastapi import FastAPI, Query
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

    ind1 = ind1.rename(columns={"score_qualite_environnement": "quality"})
    ind2 = ind2.rename(columns={"score_interet_culturel_loisir": "culture"})
    ind3 = ind3.rename(columns={"score_acces_services_publiques": "services"})
    ind4 = ind4.rename(columns={"score_acces_transport": "transport"})

    ind1 = ind1.rename(
        columns={col: f"q_{col}" for col in ind1.columns if col not in ("arrondissement", "quality")}
    )
    ind2 = ind2.rename(
        columns={col: f"c_{col}" for col in ind2.columns if col not in ("arrondissement", "culture")}
    )
    ind3 = ind3.rename(
        columns={col: f"s_{col}" for col in ind3.columns if col not in ("arrondissement", "services")}
    )
    ind4 = ind4.rename(
        columns={col: f"t_{col}" for col in ind4.columns if col not in ("arrondissement", "transport")}
    )

    scores = ind1.merge(ind2, on="arrondissement", how="outer")
    scores = scores.merge(ind3, on="arrondissement", how="outer")
    scores = scores.merge(ind4, on="arrondissement", how="outer")

    return scores


def load_gold_scores_iris():
    ind1 = pd.read_parquet(
        ROOT / "Indicateur_1" / "gold" / "score_qualite_de_vie_iris.parquet"
    ).drop(columns=["arrondissement_libelle"], errors="ignore")

    ind2 = pd.read_parquet(
        ROOT / "Indicateur_2" / "gold" / "score_interet_culturel_loisir_iris.parquet"
    ).drop(columns=["arrondissement_libelle"], errors="ignore")

    ind3 = pd.read_parquet(
        ROOT / "Indicateur_3" / "gold" / "score_acces_services_publiques_iris.parquet"
    ).drop(columns=["arrondissement_libelle"], errors="ignore")

    ind4 = pd.read_parquet(
        ROOT / "Indicateur_4" / "gold" / "score_acces_transport_iris.parquet"
    ).drop(columns=["arrondissement_libelle"], errors="ignore")

    ind1 = ind1.rename(columns={"score_qualite_environnement": "quality"})
    ind2 = ind2.rename(columns={"score_interet_culturel_loisir": "culture"})
    ind3 = ind3.rename(columns={"score_acces_services_publiques": "services"})
    ind4 = ind4.rename(columns={"score_acces_transport": "transport"})

    base_cols = ("code_iris", "nom_iris", "nom_com", "arrondissement")

    ind1 = ind1.rename(columns={col: f"q_{col}" for col in ind1.columns if col not in (*base_cols, "quality")})
    ind2 = ind2.rename(columns={col: f"c_{col}" for col in ind2.columns if col not in (*base_cols, "culture")})
    ind3 = ind3.rename(columns={col: f"s_{col}" for col in ind3.columns if col not in (*base_cols, "services")})
    ind4 = ind4.rename(columns={col: f"t_{col}" for col in ind4.columns if col not in (*base_cols, "transport")})

    scores = ind1.merge(ind2, on=list(base_cols), how="outer")
    scores = scores.merge(ind3, on=list(base_cols), how="outer")
    scores = scores.merge(ind4, on=list(base_cols), how="outer")

    return scores


def load_prices(year: int | None = None):
    prices_path = ROOT / "Indicateur_0" / "gold" / "prix_m2_arrondissement_year.parquet"
    prices = pd.read_parquet(prices_path)

    if year is None:
        year = int(prices["year"].max())

    prices = prices[prices["year"] == year].copy()

    prices["loyer_moyen"] = prices["prix_m2_mean"]
    prices["loyer_median"] = prices["prix_m2_median"]
    prices["loyer_maximum"] = prices["prix_m2_median"]

    return prices[
        [
            "arrondissement",
            "year",
            "prix_m2_median",
            "prix_m2_mean",
            "valeur_fonciere_median",
            "surface_median",
            "transactions_count",
            "loyer_moyen",
            "loyer_median",
            "loyer_maximum",
        ]
    ]


def load_prix_iris():
    path = ROOT / "Indicateur_0" / "gold" / "statistiques_loyer_iris.parquet"
    prix = pd.read_parquet(path)
    return prix[["code_iris", "loyer_moyen", "loyer_median", "loyer_maximum"]]


def add_prix_score(result: pd.DataFrame) -> pd.DataFrame:
    result[["loyer_moyen", "loyer_median", "loyer_maximum"]] = result[
        ["loyer_moyen", "loyer_median", "loyer_maximum"]
    ].fillna(0)

    valid = result[result["loyer_median"] > 0]["loyer_median"]
    median_min = valid.min() if not valid.empty else 0
    median_max = valid.max() if not valid.empty else 0

    if pd.notna(median_min) and pd.notna(median_max) and median_max > median_min:
        result["prix_score"] = result["loyer_median"].apply(
            lambda value: 50.0
            if value == 0
            else 100 - ((value - median_min) / (median_max - median_min) * 100)
        ).round(1)
    else:
        result["prix_score"] = 50.0

    return result


@app.get("/")
def root():
    return {"message": "LuxImmo API is running"}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/years")
def get_years():
    prices_path = ROOT / "Indicateur_0" / "gold" / "prix_m2_arrondissement_year.parquet"
    prices = pd.read_parquet(prices_path)
    years = sorted(prices["year"].dropna().astype(int).unique().tolist())
    return {"years": years}


@app.get("/api/arrondissements")
def get_arrondissements(year: int | None = Query(default=None)):
    scores = load_gold_scores()
    prices = load_prices(year)

    result = scores.merge(prices, on="arrondissement", how="outer")

    all_arr = pd.DataFrame({"arrondissement": list(range(1, 21))})
    result = all_arr.merge(result, on="arrondissement", how="left")

    result[["quality", "culture", "services", "transport"]] = result[
        ["quality", "culture", "services", "transport"]
    ].fillna(50)

    result = add_prix_score(result)
    result = result.fillna(0)

    return result.to_dict(orient="records")


@app.get("/api/iris")
def get_iris(year: int | None = Query(default=None)):
    scores = load_gold_scores_iris()
    prix = load_prix_iris()

    result = scores.merge(prix, on="code_iris", how="left")

    result[["quality", "culture", "services", "transport"]] = result[
        ["quality", "culture", "services", "transport"]
    ].fillna(50)

    result = add_prix_score(result)
    result = result.fillna(0)

    return result.to_dict(orient="records")


@app.get("/api/scores")
def get_scores(year: int | None = Query(default=None)):
    iris = load_paris_iris()
    scores = load_gold_scores()
    prices = load_prices(year)

    result = iris.merge(scores, on="arrondissement", how="left")
    result = result.merge(prices, on="arrondissement", how="left")

    result[["quality", "culture", "services", "transport"]] = result[
        ["quality", "culture", "services", "transport"]
    ].fillna(50)

    result = add_prix_score(result)
    result = result.fillna(0)

    return result.to_dict(orient="records")