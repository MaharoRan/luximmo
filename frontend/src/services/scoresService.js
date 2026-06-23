const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function fetchScores(year = null) {
  const url = year
    ? `${API_URL}/api/scores?year=${year}`
    : `${API_URL}/api/scores`;

  const response = await fetch(url);

  if (!response.ok) {
    throw new Error("Impossible de charger les scores depuis l’API");
  }

  const scores = await response.json();

  return Object.fromEntries(
    scores.map((item) => [item.code_iris, item])
  );
}

export async function fetchAvailableYears() {
  const response = await fetch(`${API_URL}/api/years`);

  if (!response.ok) {
    throw new Error("Impossible de charger les années");
  }

  const data = await response.json();
  return data.years;
}


export function getScoreFromData(scoresByIris, codeIris, indicator) {
  const zone = scoresByIris?.[codeIris];

  if (!zone) return 50;

  if (indicator === "price") {
    return zone.prix_m2_median ?? 0;
  }

  return zone[indicator] ?? 50;
}