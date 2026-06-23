const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Récupère les données agrégées par arrondissement depuis l'API.
 * Retourne un objet indexé par numéro d'arrondissement.
 */
export async function fetchArrondissements() {
  const response = await fetch(`${API_URL}/api/arrondissements`);

  if (!response.ok) {
    throw new Error("Impossible de charger les données depuis l'API");
  }

  const data = await response.json();

  return Object.fromEntries(
    data.map((item) => [item.arrondissement, item])
  );
}

/**
 * Récupère les données agrégées par IRIS depuis l'API.
 * Retourne un objet indexé par code_iris.
 */
export async function fetchIrisScores() {
  const response = await fetch(`${API_URL}/api/iris`);

  if (!response.ok) {
    throw new Error("Impossible de charger les données IRIS depuis l'API");
  }

  const data = await response.json();

  return Object.fromEntries(
    data.map((item) => [item.code_iris, item])
  );
}

/**
 * Récupère le score d'un indicateur pour un arrondissement donné.
 */
export function getArrScore(arrData, arrNum, indicator) {
  const zone = arrData?.[arrNum];
  if (!zone) return 50;
  return zone[indicator] ?? 50;
}

/**
 * Formate un prix en euros lisible (ex: 1 234 567 €)
 */
export function formatEuro(value) {
  if (value == null || value === 0) return "–";
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(value);
}