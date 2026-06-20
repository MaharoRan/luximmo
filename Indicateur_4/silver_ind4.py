from __future__ import annotations

from pathlib import Path
import re
import struct

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "Indicateur_4" / "raw"
SILVER_DIR = REPO_ROOT / "Indicateur_4" / "silver"

def _wkb_point_to_lon_lat(value) -> tuple[float | None, float | None]:
    if value is None:
        return None, None
    try:
        if pd.isna(value):
            return None, None
    except Exception:
        pass
    
    if isinstance(value, str):
        try:
            lat, lon = value.split(",")
            return float(lon.strip()), float(lat.strip())
        except:
            return None, None
            
    if isinstance(value, dict) and "lat" in value and "lon" in value:
        return float(value["lon"]), float(value["lat"])

    try:
        data = bytes(value)
    except TypeError:
        return None, None
        
    if len(data) < 21:
        return None, None
    byte_order = data[0]
    if byte_order == 1:
        fmt = "<dd"
    elif byte_order == 0:
        fmt = ">dd"
    else:
        return None, None
    longitude, latitude = struct.unpack_from(fmt, data, offset=5)
    return longitude, latitude

def _expand_geo_point(df: pd.DataFrame, column_name: str = "geo_point_2d") -> pd.DataFrame:
    if column_name not in df.columns:
        return df
    coordinates = df[column_name].apply(_wkb_point_to_lon_lat)
    df = df.copy()
    df["longitude"] = coordinates.apply(lambda item: item[0])
    df["latitude"] = coordinates.apply(lambda item: item[1])
    return df

def _prepare_output(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    missing_columns = [column for column in columns if column not in df.columns]
    if missing_columns:
        print(f"Colonnes manquantes: {missing_columns}")
        columns = [c for c in columns if c in df.columns]
    cleaned = df.loc[:, columns].copy()
    return cleaned

def _write_parquet(df: pd.DataFrame, output_name: str) -> None:
    output_path = SILVER_DIR / output_name
    df.to_parquet(output_path, index=False)
    print(f"Ecrit: {output_path}")

def clean_amenagements_cyclables() -> None:
    df = pd.read_parquet(RAW_DIR / "amenagements-cyclables.parquet")
    df = df[df["arrondissement"].astype(str).str.startswith("75")]
    cleaned = _prepare_output(df, ["osm_id", "amenagement", "arrondissement", "coronapiste"])
    _write_parquet(cleaned, "amenagements-cyclables.parquet")

def clean_emplacement_gares() -> None:
    df = pd.read_csv(RAW_DIR / "emplacement-des-gares-idf.csv", sep=";")
    if "Geo Point" in df.columns:
        df[["latitude", "longitude"]] = df["Geo Point"].str.split(",", expand=True).astype(float)
    cleaned = _prepare_output(df, ["gares_id", "nom_long", "mode", "exploitant", "latitude", "longitude"])
    _write_parquet(cleaned, "emplacement-des-gares-idf.parquet")

def clean_plan_de_voirie() -> None:
    df = pd.read_parquet(RAW_DIR / "plan de voirie.parquet")
    df = _expand_geo_point(df)
    cleaned = _prepare_output(df, ["OBJECTID", "geo_shape", "geo_point_2d", "longitude", "latitude"])
    _write_parquet(cleaned, "plan de voirie.parquet")

def clean_velib_stations() -> None:
    df = pd.read_parquet(RAW_DIR / "velib-emplacement-des-stations.parquet")
    if "coordonnees_geo" in df.columns:
        df[["longitude", "latitude"]] = df["coordonnees_geo"].apply(
            lambda x: pd.Series(_wkb_point_to_lon_lat(x))
        )
        df.rename(columns={"longitude": "longitude", "latitude": "latitude"}, inplace=True)
    cleaned = _prepare_output(df, ["stationcode", "name", "capacity", "coordonnees_geo", "latitude", "longitude"])
    _write_parquet(cleaned, "velib-emplacement-des-stations.parquet")

def main() -> None:
    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    clean_amenagements_cyclables()
    clean_emplacement_gares()
    clean_plan_de_voirie()
    clean_velib_stations()

if __name__ == "__main__":
    main()
