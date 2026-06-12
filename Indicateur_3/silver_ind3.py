from __future__ import annotations

from pathlib import Path
import re
import struct

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "Indicateur_3" / "raw"
SILVER_DIR = REPO_ROOT / "Indicateur_3" / "silver"

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

def clean_carte_des_points_daccueil_police() -> None:
    df = pd.read_csv(RAW_DIR / "carte-des-points-daccueil-police-a-paris.csv", sep=";")
    if "WGS84" in df.columns:
        df[["latitude", "longitude"]] = df["WGS84"].str.split(",", expand=True).astype(float)
    cleaned = _prepare_output(df, ["ardt", "service", "latitude", "longitude"])
    _write_parquet(cleaned, "carte-des-points-daccueil-police-a-paris.parquet")

def clean_ecoles_elementaires() -> None:
    df = pd.read_parquet(RAW_DIR / "etablissements-scolaires-ecoles-elementaires.parquet")
    df = _expand_geo_point(df)
    cleaned = _prepare_output(df, ["id_projet", "arr_insee", "geo_shape", "geo_point_2d", "longitude", "latitude"])
    _write_parquet(cleaned, "etablissements-scolaires-ecoles-elementaires.parquet")

def clean_hopitaux() -> None:
    df = pd.read_parquet(RAW_DIR / "hopitaux.parquet")
    cleaned = _prepare_output(df, ["finess_et", "cp_ville"])
    _write_parquet(cleaned, "hopitaux.parquet")

def clean_bureaux_poste() -> None:
    df = pd.read_parquet(RAW_DIR / "les_bureaux_de_poste_et_agences_postales_en_idf.parquet")
    df = df[df["code_postal"].astype(str).str.startswith("75")]
    cleaned = _prepare_output(df, ["libelle_du_site", "code_postal", "latitude", "longitude"])
    _write_parquet(cleaned, "les_bureaux_de_poste_et_agences_postales_en_idf.parquet")

def clean_pharmacies() -> None:
    df = pd.read_parquet(RAW_DIR / "pharmacies.parquet")
    df = df[df["cp"].astype(str).str.startswith("75")]
    cleaned = _prepare_output(df, ["nofinesset", "cp"])
    _write_parquet(cleaned, "pharmacies.parquet")

def clean_plan_de_voirie() -> None:
    df = pd.read_parquet(RAW_DIR / "plan de voirie.parquet")
    df = _expand_geo_point(df)
    cleaned = _prepare_output(df, ["OBJECTID", "geo_shape", "geo_point_2d", "longitude", "latitude"])
    _write_parquet(cleaned, "plan de voirie.parquet")

def clean_postes_publics_bibliotheques() -> None:
    df = pd.read_parquet(RAW_DIR / "postes-publics-des-bibliotheques.parquet")
    if "position" in df.columns:
        df[["latitude", "longitude"]] = df["position"].apply(
            lambda x: pd.Series(_wkb_point_to_lon_lat(x)) if x is not None else pd.Series([None, None])
        )
    cleaned = _prepare_output(df, ["localisation", "nombre_d_ordinateurs", "longitude", "latitude"])
    _write_parquet(cleaned, "postes-publics-des-bibliotheques.parquet")

def clean_secteurs_scolaires_colleges() -> None:
    df = pd.read_parquet(RAW_DIR / "secteurs-scolaires-colleges.parquet")
    cleaned = _prepare_output(df, ["id_projet", "lib_etab_1", "zone_commune"])
    _write_parquet(cleaned, "secteurs-scolaires-colleges.parquet")

def clean_secteurs_scolaires_maternelles() -> None:
    df = pd.read_parquet(RAW_DIR / "secteurs-scolaires-maternelles.parquet")
    cleaned = _prepare_output(df, ["id_projet", "lib_etab_1", "zone_commune"])
    _write_parquet(cleaned, "secteurs-scolaires-maternelles.parquet")

def main() -> None:
    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    clean_carte_des_points_daccueil_police()
    clean_ecoles_elementaires()
    clean_hopitaux()
    clean_bureaux_poste()
    clean_pharmacies()
    clean_plan_de_voirie()
    clean_postes_publics_bibliotheques()
    clean_secteurs_scolaires_colleges()
    clean_secteurs_scolaires_maternelles()

if __name__ == "__main__":
    main()
