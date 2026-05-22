from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILE = PROJECT_ROOT / "Indicateur_0" / "raw" / "dvf.csv"
SILVER_DIR = PROJECT_ROOT / "Indicateur_0" / "silver"
SELECTED_COLUMNS = [
    "date_mutation",
    "valeur_fonciere",
    "code_postal",
    "longitude",
    "latitude",
]


def _load_dvf(source_file: Path) -> pd.DataFrame:
    if not source_file.exists():
        raise FileNotFoundError(f"Fichier source introuvable: {source_file}")

    df = pd.read_csv(source_file, dtype={"code_postal": "string"})

    missing_columns = [column for column in SELECTED_COLUMNS if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Colonnes manquantes dans dvf.csv: {missing_columns}")

    df = df.loc[:, SELECTED_COLUMNS].copy()
    df = df.dropna(subset=SELECTED_COLUMNS)
    df["code_postal"] = df["code_postal"].astype("string").str.zfill(5)
    df = df[df["code_postal"].str.startswith("75")]

    return df


def _arrondissement_from_code_postal(code_postal: str) -> str:
    arrondissement = code_postal[-2:]
    return arrondissement


def _export_parquet_by_arrondissement(df: pd.DataFrame, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for code_postal, group in df.groupby("code_postal", dropna=False):
        arrondissement = _arrondissement_from_code_postal(str(code_postal))
        output_file = output_dir / f"paris_{arrondissement}.parquet"
        group.to_parquet(output_file, index=False)
        print(f"Ecrit: {output_file} ({len(group)} lignes)")


def main() -> None:
    df = _load_dvf(SOURCE_FILE)
    _export_parquet_by_arrondissement(df, SILVER_DIR)


if __name__ == "__main__":
    main()
