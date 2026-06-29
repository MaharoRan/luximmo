import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from datetime import timedelta

import pandas as pd
from fastapi import FastAPI, Query, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from auth import (
    get_current_user,
    verify_password,
    FAKE_USERS_DB,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

from batch import update_chantiers_batch, update_trafic_batch, batch_status

ROOT = Path(__file__).resolve().parents[1]

@asynccontextmanager
async def lifespan(app: FastAPI):
    task_chantiers = asyncio.create_task(update_chantiers_batch())
    task_trafic = asyncio.create_task(update_trafic_batch())
    yield
    task_chantiers.cancel()
    task_trafic.cancel()

app = FastAPI(title="LuxImmo API", lifespan=lifespan)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

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

    prices["loyer_moyen"] = prices["prix_m2_moyen"]
    prices["loyer_median"] = prices["prix_m2_median"]
    prices["loyer_maximum"] = prices["prix_m2_maximum"]

    cols_to_keep = [
        "arrondissement", "year", "prix_vente_moyen", "prix_vente_median",
        "surface_moyenne", "surface_mediane", "prix_m2_moyen", "prix_m2_median",
        "prix_m2_minimum", "prix_m2_maximum", "transactions_count",
        "loyer_moyen", "loyer_median", "loyer_maximum"
    ]
    categories = [f"{t}_T{p}" for t in ["Appartement", "Maison"] for p in ["1", "2", "3", "4", "5+"]]
    existing_cols = [c for c in cols_to_keep + categories if c in prices.columns]
    
    return prices[existing_cols]


def load_prix_iris(year: int | None = None):
    path_year = ROOT / "Indicateur_0" / "gold" / "statistiques_loyer_iris_year.parquet"
    path_global = ROOT / "Indicateur_0" / "gold" / "statistiques_loyer_iris.parquet"

    if path_year.exists():
        prix = pd.read_parquet(path_year)

        if year is None:
            year = int(prix["year"].dropna().max())

        prix = prix[prix["year"] == year].copy()
    else:
        prix = pd.read_parquet(path_global)

    prix["loyer_moyen"] = prix.get("prix_m2_moyen", prix.get("loyer_moyen"))
    prix["loyer_median"] = prix.get("prix_m2_median", prix.get("loyer_median"))
    prix["loyer_maximum"] = prix.get("prix_m2_maximum", prix.get("loyer_maximum"))

    cols_to_keep = [
        "code_iris", "year", "prix_vente_moyen", "prix_vente_median",
        "surface_moyenne", "surface_mediane", "prix_m2_moyen",
        "prix_m2_median", "prix_m2_minimum", "prix_m2_maximum",
        "transactions_count", "loyer_moyen", "loyer_median", "loyer_maximum"
    ]
    categories = [f"{t}_T{p}" for t in ["Appartement", "Maison"] for p in ["1", "2", "3", "4", "5+"]]
    existing_cols = [c for c in cols_to_keep + categories if c in prix.columns]
    return prix[existing_cols]


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


@app.post("/api/token")
@limiter.limit("5/minute")
def login_for_access_token(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    user_dict = FAKE_USERS_DB.get(form_data.username)
    if not user_dict:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not verify_password(form_data.password, user_dict["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_dict["username"]}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/")
def root():
    return {"message": "LuxImmo API is running"}


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/years")
@limiter.limit("60/minute")
def get_years(request: Request, current_user: dict = Depends(get_current_user)):
    prices_path = ROOT / "Indicateur_0" / "gold" / "prix_m2_arrondissement_year.parquet"
    prices = pd.read_parquet(prices_path)
    years = sorted(prices["year"].dropna().astype(int).unique().tolist())
    return {"years": years}


@app.get("/api/arrondissements")
@limiter.limit("60/minute")
def get_arrondissements(request: Request, year: int | None = Query(default=None), current_user: dict = Depends(get_current_user)):
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
@limiter.limit("60/minute")
def get_iris(request: Request, year: int | None = Query(default=None), current_user: dict = Depends(get_current_user)):
    scores = load_gold_scores_iris()
    prix = load_prix_iris(year)

    result = scores.merge(prix, on="code_iris", how="left")

    result[["quality", "culture", "services", "transport"]] = result[
        ["quality", "culture", "services", "transport"]
    ].fillna(50)

    result = add_prix_score(result)
    result = result.fillna(0)

    return result.to_dict(orient="records")


@app.get("/api/scores")
@limiter.limit("60/minute")
def get_scores(request: Request, year: int | None = Query(default=None), current_user: dict = Depends(get_current_user)):
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
@app.get('/api/batch-status')
@limiter.limit("60/minute")
def get_batch_status(request: Request, current_user: dict = Depends(get_current_user)):
    return batch_status

