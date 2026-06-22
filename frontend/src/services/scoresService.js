const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function fetchScores() {
  const response = await fetch(`${API_URL}/api/scores`);

  if (!response.ok) {
    throw new Error("Impossible de charger les scores depuis l’API");
  }

  const scores = await response.json();

  return Object.fromEntries(
    scores.map((item) => [item.code_iris, item])
  );
}

export function getScoreFromData(scoresByIris, codeIris, indicator) {
  const zone = scoresByIris?.[codeIris];

  if (!zone) {
    return 50;
  }

  // cas spécial : prix immobilier
  if (indicator === "price") {
    return zone.prix_m2_median ?? 0;
  }

  return zone[indicator] ?? 50;
}

// utile pour normaliser les prix sur la carte
export function getPriceRange(scoresByIris) {
  const values = Object.values(scoresByIris)
    .map((zone) => zone.prix_m2_median)
    .filter(Boolean);

  if (!values.length) {
    return { min: 0, max: 15000 };
  }

  return {
    min: Math.min(...values),
    max: Math.max(...values),
  };
}