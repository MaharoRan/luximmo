from __future__ import annotations

from pathlib import Path
import re
import struct

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "Indicateur_2" / "raw"
SILVER_DIR = REPO_ROOT / "Indicateur_2" / "silver"

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

def _normalize_arrondissement(value):
    if value is None:
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("75"):
            return stripped
        match = re.search(r"PARIS\s+(\d{1,2})(?:ER|E)\s+ARRDT", stripped)
        if match:
            return f"750{int(match.group(1)):02d}"
    return value

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

def clean_ilots_fraicheur_espaces_verts() -> None:
    df = pd.read_parquet(RAW_DIR / "ilots-de-fraicheur-espaces-verts-frais.parquet")
    df = _expand_geo_point(df)
    cleaned = _prepare_output(df, ["nom", "type", "arrondissement", "geo_shape", "geo_point_2d", "surf_veget_sup8m_2024", "longitude", "latitude"])
    _write_parquet(cleaned, "ilots-de-fraicheur-espaces-verts-frais.parquet")

def clean_les_arbres() -> None:
    df = pd.read_parquet(RAW_DIR / "les-arbres.parquet")
    df = df.copy()
    df = df[df["arrondissement"].astype(str).str.startswith("PARIS")]
    df["arrondissement"] = df["arrondissement"].apply(_normalize_arrondissement)
    df = _expand_geo_point(df)
    cleaned = _prepare_output(df, ["arrondissement", "geo_point_2d", "longitude", "latitude"])
    _write_parquet(cleaned, "les-arbres.parquet")

def clean_lieux_de_tournage() -> None:
    df = pd.read_parquet(RAW_DIR / "lieux-de-tournage-a-paris.parquet")
    df = _expand_geo_point(df)
    cleaned = _prepare_output(df, ["id_lieu", "ardt_lieu", "geo_shape", "geo_point_2d", "longitude", "latitude"])
    _write_parquet(cleaned, "lieux-de-tournage-a-paris.parquet")

def clean_liste_des_associations_parisiennes() -> None:
    df = pd.read_parquet(RAW_DIR / "liste_des_associations_parisiennes.parquet")
    cleaned = _prepare_output(df, ["pr_nom_statutaire", "cp_adresse_code_postal", "sa_libell_domaine_d_activit"])
    _write_parquet(cleaned, "liste_des_associations_parisiennes.parquet")

def clean_plan_de_voirie() -> None:
    df = pd.read_parquet(RAW_DIR / "plan de voirie.parquet")
    df = _expand_geo_point(df)
    cleaned = _prepare_output(df, ["OBJECTID", "geo_shape", "geo_point_2d", "longitude", "latitude"])
    _write_parquet(cleaned, "plan de voirie.parquet")

def clean_que_faire() -> None:
    df = pd.read_parquet(RAW_DIR / "que-faire-a-paris.parquet")
    cleaned = _prepare_output(df, ["id", "title", "date_start", "date_end", "address_name"])
    _write_parquet(cleaned, "que-faire-a-paris.parquet")

def clean_zones_touristiques_internationales() -> None:
    df = pd.read_parquet(RAW_DIR / "zones-touristiques-internationales.parquet")
    df = _expand_geo_point(df)
    cleaned = _prepare_output(df, ["name", "geo_shape", "geo_point_2d", "longitude", "latitude"])
    _write_parquet(cleaned, "zones-touristiques-internationales.parquet")

def main() -> None:
    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    clean_ilots_fraicheur_espaces_verts()
    clean_les_arbres()
    clean_lieux_de_tournage()
    clean_liste_des_associations_parisiennes()
    clean_plan_de_voirie()
    clean_que_faire()
    clean_zones_touristiques_internationales()

if __name__ == "__main__":
    main()
