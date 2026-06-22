from __future__ import annotations

from pathlib import Path
import re

import pandas as pd
from shapely import wkb
from shapely.geometry import Point
from shapely.strtree import STRtree


REPO_ROOT = Path(__file__).resolve().parents[1]
GEO_DIR = REPO_ROOT / "geo"
SILVER_DIR = REPO_ROOT / "Indicateur_1" / "silver"
GOLD_DIR = REPO_ROOT / "Indicateur_1" / "gold"

PARIS_ARRONDISSEMENT_RE = re.compile(r"Paris\s+(\d{1,2})e\s+Arrondissement", re.IGNORECASE)
POSTAL_75_RE = re.compile(r"75(\d{3})")


def _safe_numeric_series(series: pd.Series) -> pd.Series:
	return pd.to_numeric(series, errors="coerce")


def _extract_paris_arrondissement(value) -> int | None:
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


def _load_paris_iris() -> pd.DataFrame:
	iris = pd.read_parquet(GEO_DIR / "iris.parquet")
	iris = iris[iris["nom_com"].astype(str).str.contains("Paris", case=False, na=False)].copy()
	iris["arrondissement"] = iris["nom_com"].apply(_extract_paris_arrondissement)
	iris["geometry"] = iris["geo_shape"].apply(lambda value: wkb.loads(bytes(value)) if pd.notna(value) else None)
	iris = iris.dropna(subset=["arrondissement", "geometry"]).copy()
	iris["arrondissement"] = iris["arrondissement"].astype(int)
	return iris[["code_iris", "nom_iris", "nom_com", "arrondissement", "geometry"]]


def _attach_arrondissement_from_points(df: pd.DataFrame, lon_col: str, lat_col: str, iris: pd.DataFrame) -> pd.DataFrame:
	working = df.copy()
	working[lon_col] = _safe_numeric_series(working[lon_col])
	working[lat_col] = _safe_numeric_series(working[lat_col])
	working = working.dropna(subset=[lon_col, lat_col]).copy()
	if working.empty:
		working["arrondissement"] = pd.Series(dtype="int64")
		return working

	iris_geometries = iris["geometry"].tolist()
	iris_arrondissements = iris["arrondissement"].tolist()
	iris_lookup = {geometry.wkb: arrondissement for geometry, arrondissement in zip(iris_geometries, iris_arrondissements)}
	tree = STRtree(iris_geometries)

	arrondissements: list[int | None] = []
	for longitude, latitude in zip(working[lon_col], working[lat_col]):
		point = Point(float(longitude), float(latitude))
		arrondissement = None
		for candidate in tree.query(point):
			if hasattr(candidate, "covers"):
				geometry = candidate
				candidate_arrondissement = iris_lookup.get(candidate.wkb)
			else:
				geometry = iris_geometries[int(candidate)]
				candidate_arrondissement = iris_arrondissements[int(candidate)]

			if geometry.covers(point):
				arrondissement = candidate_arrondissement
				break

		arrondissements.append(arrondissement)

	working["arrondissement"] = arrondissements
	working = working.dropna(subset=["arrondissement"]).copy()
	working["arrondissement"] = working["arrondissement"].astype(int)
	return working


def _normalize_weights(series: pd.Series) -> pd.Series:
	maximum = series.max(skipna=True)
	if pd.isna(maximum) or maximum <= 0:
		return series * 0
	return series / maximum


def _first_available_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
	for c in candidates:
		if c in df.columns:
			return c
	return None


def _load_trees_scores() -> pd.DataFrame:
	df = pd.read_parquet(SILVER_DIR / "les-arbres.parquet")
	df = df.copy()
	# try several common arrondissement-like columns
	col = _first_available_column(df, ["arrondissement", "ardt", "ardt_lieu", "cp", "cp_adresse_code_postal", "code_postal"])
	if col:
		df["arrondissement"] = df[col].apply(_extract_paris_arrondissement)
	else:
		df["arrondissement"] = None

	# ensure column exists even if previous attempts failed
	if "arrondissement" not in df.columns:
		df["arrondissement"] = None
	if "arrondissement" not in df.columns:
		df["arrondissement"] = None
	# ensure arrondissement column exists even if previous attempts failed
	if "arrondissement" not in df.columns:
		df["arrondissement"] = None
	# ensure arrondissement column exists before dropping
	if "arrondissement" not in df.columns:
		df["arrondissement"] = None
	# ensure arrondissement column exists before dropna
	if "arrondissement" not in df.columns:
		df["arrondissement"] = None
	if "arrondissement" not in df.columns:
		df["arrondissement"] = None
	df = df.dropna(subset=["arrondissement"]).copy()
	df["arrondissement"] = df["arrondissement"].astype(int)
	grouped = df.groupby("arrondissement", as_index=False).agg(trees_count=("arrondissement", "count"))
	grouped["trees_raw"] = grouped["trees_count"]
	return grouped


def _load_freshness_islands_scores() -> pd.DataFrame:
	df = pd.read_parquet(SILVER_DIR / "ilots-de-fraicheur-espaces-verts-frais.parquet")
	df = df.copy()
	col = _first_available_column(df, ["arrondissement", "ardt", "ardt_lieu", "cp", "code_postal"])
	if col:
		df["arrondissement"] = df[col].apply(_extract_paris_arrondissement)
	else:
		if "longitude" in df.columns and "latitude" in df.columns:
			iris = _load_paris_iris()
			df = _attach_arrondissement_from_points(df, "longitude", "latitude", iris)

	# ensure arrondissement column exists even if previous attempts failed
	if "arrondissement" not in df.columns:
		df["arrondissement"] = None
	df = df.dropna(subset=["arrondissement"]).copy()
	df["arrondissement"] = df["arrondissement"].astype(int)
	grouped = df.groupby("arrondissement", as_index=False).agg(islands_count=("nom", "count") if "nom" in df.columns else ("arrondissement", "count"))
	grouped["islands_raw"] = grouped.iloc[:, 1]
	return grouped


def _load_islands_equipements_scores() -> pd.DataFrame:
	df = pd.read_parquet(SILVER_DIR / "ilots-de-fraicheur-equipements-activites.parquet")
	df = df.copy()
	col = _first_available_column(df, ["arrondissement", "ardt", "ardt_lieu", "cp", "code_postal"])
	if col:
		df["arrondissement"] = df[col].apply(_extract_paris_arrondissement)
	else:
		if "longitude" in df.columns and "latitude" in df.columns:
			iris = _load_paris_iris()
			df = _attach_arrondissement_from_points(df, "longitude", "latitude", iris)

	df = df.dropna(subset=["arrondissement"]).copy()
	df["arrondissement"] = df["arrondissement"].astype(int)
	grouped = df.groupby("arrondissement", as_index=False).agg(islands_equip_count=("arrondissement", "count"))
	grouped["islands_equip_raw"] = grouped["islands_equip_count"]
	return grouped



def _load_sanisettes_scores() -> pd.DataFrame:
	df = pd.read_parquet(SILVER_DIR / "sanisettesparis.parquet")
	df = df.copy()
	col = _first_available_column(df, ["arrondissement", "ardt", "cp", "cp_adresse_code_postal", "code_postal"])
	if col:
		df["arrondissement"] = df[col].apply(_extract_paris_arrondissement)
	else:
		if "longitude" in df.columns and "latitude" in df.columns:
			iris = _load_paris_iris()
			df = _attach_arrondissement_from_points(df, "longitude", "latitude", iris)

	df = df.dropna(subset=["arrondissement"]).copy()
	df["arrondissement"] = df["arrondissement"].astype(int)
	grouped = df.groupby("arrondissement", as_index=False).agg(sanisettes_count=("arrondissement", "count"))
	grouped["sanisettes_raw"] = grouped["sanisettes_count"]
	return grouped


def _load_tourism_zones_scores(iris: pd.DataFrame) -> pd.DataFrame:
	df = pd.read_parquet(SILVER_DIR / "zones-touristiques-internationales.parquet")
	df = df.copy()
	df = _attach_arrondissement_from_points(df, "longitude", "latitude", iris)
	grouped = df.groupby("arrondissement", as_index=False).agg(zones_tourism=("name", "count"))
	grouped["zones_tourism_raw"] = grouped["zones_tourism"]
	return grouped


def build_gold_score() -> pd.DataFrame:
	iris = _load_paris_iris()

	trees = _load_trees_scores()
	islands = _load_freshness_islands_scores()
	islands_equip = _load_islands_equipements_scores()
	sanisettes = _load_sanisettes_scores()
	zones = _load_tourism_zones_scores(iris)

	score = pd.DataFrame({"arrondissement": list(range(1, 21))})
	score = score.merge(trees, on="arrondissement", how="left")
	score = score.merge(islands, on="arrondissement", how="left")
	score = score.merge(islands_equip, on="arrondissement", how="left")
	score = score.merge(sanisettes, on="arrondissement", how="left")
	score = score.merge(zones, on="arrondissement", how="left")

	numeric_columns = [
		"trees_count",
		"trees_raw",
		"islands_count",
		"islands_raw",
		"islands_equip_count",
		"islands_equip_raw",
		"sanisettes_count",
		"sanisettes_raw",
		"zones_tourism",
		"zones_tourism_raw",
	]
	for column in numeric_columns:
		if column not in score.columns:
			score[column] = 0
		score[column] = score[column].fillna(0)

	# normalize positives
	score["trees_norm"] = _normalize_weights(score["trees_raw"]) 
	score["islands_norm"] = _normalize_weights(score["islands_raw"]) 
	score["islands_equip_norm"] = _normalize_weights(score["islands_equip_raw"]) 

	# normalize negatives
	score["sanisettes_norm"] = _normalize_weights(score["sanisettes_raw"]) 
	score["zones_tourism_norm"] = _normalize_weights(score["zones_tourism_raw"]) 

	# positive equally weighted (3 items)
	score["positive_score"] = (
		(1.0/3.0) * score["trees_norm"]
		+ (1.0/3.0) * score["islands_norm"]
		+ (1.0/3.0) * score["islands_equip_norm"]
	)

	# negative penalty: average of normalized negatives
	score["negative_score"] = 0.5 * (score["sanisettes_norm"] + score["zones_tourism_norm"]) / 1.0

	# final score: positive minus a fraction of negatives, clipped to [0,1]
	raw_final = score["positive_score"] - 0.5 * score["negative_score"]
	raw_final = raw_final.clip(lower=0)
	score["score_qualite_environnement"] = (10 + 90 * raw_final).round(2)

	score["arrondissement_libelle"] = score["arrondissement"].apply(lambda value: f"Paris {int(value)}e Arrondissement")
	score = score.sort_values("score_qualite_environnement", ascending=False).reset_index(drop=True)

	return score[
		[
			"arrondissement",
			"arrondissement_libelle",
			"score_qualite_environnement",
			"trees_count",
			"islands_count",
			"islands_equip_count",
			"sanisettes_count",
			"zones_tourism",
			"trees_norm",
			"islands_norm",
			"islands_equip_norm",
			"sanisettes_norm",
			"zones_tourism_norm",
		]
	]


def main() -> None:
	GOLD_DIR.mkdir(parents=True, exist_ok=True)
	score = build_gold_score()
	output_path = GOLD_DIR / "score_qualite_de_vie.parquet"
	score.to_parquet(output_path, index=False)
	print(f"Ecrit: {output_path}")


if __name__ == "__main__":
	main()

