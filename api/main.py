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


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/scores")
def get_scores():
    # temporaire : fallback JSON du front
    # plus tard : remplacer ce chemin par Indicateur_X/gold/...
    data_path = ROOT / "frontend" / "public" / "data" / "scores.json"

    if not data_path.exists():
        return []

    df = pd.read_json(data_path)
    return df.to_dict(orient="records")