from __future__ import annotations

import re
from pathlib import Path
import pandas as pd
from shapely import wkb
from shapely.geometry import Point
from shapely.strtree import STRtree

REPO_ROOT = Path(__file__).resolve().parents[1]
GEO_DIR = REPO_ROOT / "geo"

PARIS_ARRONDISSEMENT_RE = re.compile(r"Paris\s+(\d{1,2})e\s+Arrondissement", re.IGNORECASE)
POSTAL_75_RE = re.compile(r"75(\d{3})")

def safe_numeric_series(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")

def extract_paris_arrondissement(value) -> int | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    match = PARIS_ARRONDISSEMENT_RE.search(text)
    if match:
        arrondissement = int(match.group(1))
        if 1 <= arrondissement <= 20:
            return arrondissement

    match = POSTAL_75_RE.search(text)
    if match:
        arrondissement = int(match.group(1)) % 100
        if 1 <= arrondissement <= 20:
            return arrondissement

    if text.isdigit():
        arrondissement = int(text)
        if 1 <= arrondissement <= 20:
            return arrondissement

    match = re.search(r"(\d{1,2})", text)
    if match:
        arrondissement = int(match.group(1))
        if 1 <= arrondissement <= 20:
            return arrondissement

    return None

def load_paris_iris() -> pd.DataFrame:
    iris = pd.read_parquet(GEO_DIR / "iris.parquet")
    iris = iris[iris["nom_com"].astype(str).str.contains("Paris", case=False, na=False)].copy()
    iris["arrondissement"] = iris["nom_com"].apply(extract_paris_arrondissement)
    iris["geometry"] = iris["geo_shape"].apply(lambda value: wkb.loads(bytes(value)) if pd.notna(value) else None)
    iris = iris.dropna(subset=["arrondissement", "geometry"]).copy()
    iris["arrondissement"] = iris["arrondissement"].astype(int)
    return iris[["code_iris", "nom_iris", "nom_com", "arrondissement", "geometry"]]

def attach_iris_from_points(df: pd.DataFrame, lon_col: str, lat_col: str, iris: pd.DataFrame) -> pd.DataFrame:
    working = df.copy()
    working[lon_col] = safe_numeric_series(working[lon_col])
    working[lat_col] = safe_numeric_series(working[lat_col])
    working = working.dropna(subset=[lon_col, lat_col]).copy()
    if working.empty:
        working["code_iris"] = pd.Series(dtype="str")
        working["arrondissement"] = pd.Series(dtype="int64")
        return working

    iris_geometries = iris["geometry"].tolist()
    iris_codes = iris["code_iris"].tolist()
    iris_arrondissements = iris["arrondissement"].tolist()
    iris_lookup = {geometry.wkb: (code, arr) for geometry, code, arr in zip(iris_geometries, iris_codes, iris_arrondissements)}
    tree = STRtree(iris_geometries)

    codes: list[str | None] = []
    arrondissements: list[int | None] = []
    
    lon_vals = working[lon_col].values
    lat_vals = working[lat_col].values
    
    for longitude, latitude in zip(lon_vals, lat_vals):
        point = Point(float(longitude), float(latitude))
        code = None
        arrondissement = None
        for candidate in tree.query(point):
            if hasattr(candidate, "covers"):
                geometry = candidate
                candidate_data = iris_lookup.get(candidate.wkb)
                if candidate_data:
                    candidate_code, candidate_arr = candidate_data
            else:
                geometry = iris_geometries[int(candidate)]
                candidate_code = iris_codes[int(candidate)]
                candidate_arr = iris_arrondissements[int(candidate)]

            if geometry.covers(point):
                code = candidate_code
                arrondissement = candidate_arr
                break

        codes.append(code)
        arrondissements.append(arrondissement)

    working["code_iris"] = codes
    working["arrondissement"] = arrondissements
    working = working.dropna(subset=["code_iris", "arrondissement"]).copy()
    working["arrondissement"] = working["arrondissement"].astype(int)
    return working
