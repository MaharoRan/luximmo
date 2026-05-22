from __future__ import annotations

from pathlib import Path
import re
import struct

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = REPO_ROOT / "Indicateur_1" / "raw"
SILVER_DIR = REPO_ROOT / "Indicateur_1" / "silver"


def _wkb_point_to_lon_lat(value) -> tuple[float | None, float | None]:
    if value is None:
        return None, None

    try:
        if pd.isna(value):
            return None, None
    except Exception:
        pass

    data = bytes(value)
    if len(data) < 21:
        return None, None

    byte_order = data[0]
    if byte_order == 1:
        fmt = "<dd"
    elif byte_order == 0:
        fmt = ">dd"
    else:
        raise ValueError(f"Octet d'endianess WKB invalide: {byte_order}")

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
        raise ValueError(f"Colonnes manquantes: {missing_columns}")

    cleaned = df.loc[:, columns].copy()
    cleaned = cleaned.dropna(subset=columns)
    return cleaned


def _write_parquet(df: pd.DataFrame, output_name: str) -> None:
    output_path = SILVER_DIR / output_name
    df.to_parquet(output_path, index=False)
    print(f"Ecrit: {output_path}")


def clean_eclairage_public() -> None:
    df = pd.read_parquet(RAW_DIR / "eclairage-public.parquet")
    cleaned = _prepare_output(df, ["x_wgs84", "y_wgs84", "lib_ouvrag"])
    _write_parquet(cleaned, "eclairage-public.parquet")


def clean_ilots_fraicheur_equipements() -> None:
    df = pd.read_parquet(RAW_DIR / "ilots-de-fraicheur-equipements-activites.parquet")
    df = _expand_geo_point(df)
    cleaned = _prepare_output(df, ["nom", "type", "arrondissement", "geo_shape", "geo_point_2d", "longitude", "latitude"])
    _write_parquet(cleaned, "ilots-de-fraicheur-equipements-activites.parquet")


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


def clean_sanisettes() -> None:
    df = pd.read_parquet(RAW_DIR / "sanisettesparis.parquet")
    df = _expand_geo_point(df)
    cleaned = _prepare_output(df, ["arrondissement", "statut", "type", "geo_shape", "geo_point_2d", "longitude", "latitude"])
    _write_parquet(cleaned, "sanisettesparis.parquet")


def clean_zones_touristiques() -> None:
    df = pd.read_parquet(RAW_DIR / "zones-touristiques-internationales.parquet")
    df = _expand_geo_point(df)
    cleaned = _prepare_output(df, ["name", "geo_shape", "geo_point_2d", "longitude", "latitude"])
    _write_parquet(cleaned, "zones-touristiques-internationales.parquet")


def main() -> None:
    SILVER_DIR.mkdir(parents=True, exist_ok=True)

    clean_eclairage_public()
    clean_ilots_fraicheur_equipements()
    clean_ilots_fraicheur_espaces_verts()
    clean_les_arbres()
    clean_sanisettes()
    clean_zones_touristiques()


if __name__ == "__main__":
    main()
