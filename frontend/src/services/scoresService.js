export async function fetchScores() {
  const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

  const response = await fetch(`${API_URL}/api/scores`);

  if (!response.ok) {
    throw new Error("Impossible de charger les scores");
  }

  const scores = await response.json();

  // transforme tableau -> objet indexé par code_iris
  return Object.fromEntries(
    scores.map((item) => [item.code_iris, item])
  );
}

export function getScoreFromData(scoresByIris, codeIris, indicator) {
  // si on a un vrai score dans scores.json
  const existingScore = scoresByIris?.[codeIris]?.[indicator];

  if (existingScore !== undefined) {
    return existingScore;
  }

  // fallback temporaire : score généré dynamiquement
  const base = Number(String(codeIris).slice(-3)) || 50;

  if (indicator === "quality") return 40 + (base % 55);
  if (indicator === "culture") return 30 + (base % 65);
  if (indicator === "services") return 35 + (base % 60);
  if (indicator === "transport") return 45 + (base % 50);

  return 50;
}