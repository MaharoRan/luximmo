const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function fetchScores() {
  const response = await fetch(`${API_URL}/api/scores`);

  if (!response.ok) {
    throw new Error("Impossible de charger les scores depuis l’API");
  }

  const scores = await response.json();

  // transforme tableau -> objet indexé par code_iris
  return Object.fromEntries(
    scores.map((item) => [item.code_iris, item])
  );
}

export function getScoreFromData(scoresByIris, codeIris, indicator) {
  // récupération du score réel depuis l'API
  const zone = scoresByIris?.[codeIris];

  if (!zone) {
    return 50; // fallback neutre si zone absente
  }

  return zone[indicator] ?? 50;
}