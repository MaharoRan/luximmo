import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_BASE = os.path.join(SCRIPT_DIR, "raw")
SILVER_BASE = os.path.join(SCRIPT_DIR, "silver")
os.makedirs(SILVER_BASE, exist_ok=True)

def clean_columns(df):
    cleaned = {}
    for c in df.columns:
        clean_name = re.sub(r"[ ,;{}()\n\t=\-]", "_", c)
        cleaned[c] = clean_name
    return df.rename(columns=cleaned)

def process_dvf():
    print("Traitement DVF")
    paths = [f"{RAW_BASE}/ValeursFoncieres-{year}.csv" for year in range(2021, 2026)]
    dfs = []
    for p in paths:
        if os.path.exists(p):
            dfs.append(pd.read_csv(p, sep=";", low_memory=False))
    if not dfs: return

    df = pd.concat(dfs, ignore_index=True)
    df = df[df["Code departement"].astype(str).str.startswith("75") | df["Code postal"].astype(str).str.startswith("75")]
    df["Date mutation formatee"] = pd.to_datetime(df["Date mutation"], format="%d/%m/%Y", errors="coerce")
    df = df[(df["Date mutation formatee"].dt.year >= 2021) & (df["Date mutation formatee"].dt.year <= 2025)]
    
    if "Latitude" in df.columns:
        df["latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    else: df["latitude"] = None
    if "Longitude" in df.columns:
        df["longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")
    else: df["longitude"] = None
    
    geometry = [Point(lon, lat) if pd.notnull(lat) and pd.notnull(lon) else None for lat, lon in zip(df["latitude"], df["longitude"])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
    gdf = clean_columns(gdf)
    for c in gdf.columns:
        if c != "geometry" and gdf[c].dtype == object:
            gdf[c] = gdf[c].astype("string")
    gdf.to_parquet(f"{SILVER_BASE}/dvf_paris.parquet", engine="pyarrow", compression="snappy")

if __name__ == "__main__":
    process_dvf()


