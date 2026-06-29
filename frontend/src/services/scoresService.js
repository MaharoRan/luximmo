const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function authFetch(url, options = {}) {
  const token = localStorage.getItem("luximmo_token");
  const headers = {
    ...options.headers,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  
  const response = await fetch(url, { ...options, headers });
  
  if (response.status === 401) {
    localStorage.removeItem("luximmo_token");
    window.location.reload();
  }

  if (response.status === 429) {
    alert("Trop de requêtes ! Veuillez patienter un instant avant de continuer.");
    throw new Error("Trop de requêtes (Rate limit dépassé).");
  }
  
  return response;
}

export async function fetchScores(year = null) {
  const url = year
    ? `${API_URL}/api/scores?year=${year}`
    : `${API_URL}/api/scores`;

  const response = await authFetch(url);

  if (!response.ok) {
    throw new Error("Impossible de charger les scores depuis l’API");
  }

  const data = await response.json();

  return Object.fromEntries(data.map((item) => [item.code_iris, item]));
}

export async function fetchAvailableYears() {
  const response = await authFetch(`${API_URL}/api/years`);

  if (!response.ok) {
    throw new Error("Impossible de charger les années");
  }

  const data = await response.json();
  return data.years;
}

export async function fetchArrondissements(year = null) {
  const url = year
    ? `${API_URL}/api/arrondissements?year=${year}`
    : `${API_URL}/api/arrondissements`;

  const response = await authFetch(url);

  if (!response.ok) {
    throw new Error("Impossible de charger les arrondissements depuis l’API");
  }

  const data = await response.json();

  return Object.fromEntries(data.map((item) => [item.arrondissement, item]));
}

export async function fetchIrisScores(year = null) {
  const url = year
    ? `${API_URL}/api/iris?year=${year}`
    : `${API_URL}/api/iris`;

  const response = await authFetch(url);

  if (!response.ok) {
    throw new Error("Impossible de charger les données IRIS depuis l’API");
  }

  const data = await response.json();

  return Object.fromEntries(data.map((item) => [item.code_iris, item]));
}

export function getScoreFromData(scoresByIris, codeIris, indicator) {
  const zone = scoresByIris?.[codeIris];

  if (!zone) return 50;

  if (indicator === "price") {
    return zone.prix_m2_median ?? 0;
  }

  if (indicator === "prix_score") {
    return zone.prix_score ?? 50;
  }

  return zone[indicator] ?? 50;
}

export function getArrScore(arrData, arrNum, indicator) {
  const zone = arrData?.[arrNum];
  if (!zone) return 50;
  return zone[indicator] ?? 50;
}

export function formatEuro(value) {
  if (value == null || value === 0) return "–";

  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  }).format(value);
}