import { useEffect, useState } from "react";
import { fetchScores, getScoreFromData } from "../services/scoresService";

const indicatorLabels = {
  quality: "Qualité de vie",
  culture: "Culture & loisirs",
  services: "Services publics",
  transport: "Transports",
  price: "Prix immobilier",
};

function formatScore(value, indicator) {
  if (indicator === "price") {
    return `${Number(value).toLocaleString("fr-FR")} €/m²`;
  }

  return `${value}/100`;
}

function RankingPanel({ selectedIndicator, selectedYear }) {
  const [scoresByIris, setScoresByIris] = useState({});

  useEffect(() => {
    if (!selectedYear) return;
    fetchScores(selectedYear).then(setScoresByIris);
  }, [selectedYear]);

  const ranking = Object.values(scoresByIris)
    .map((zone) => ({
      code_iris: zone.code_iris,
      nom_iris: zone.nom_iris || zone.code_iris,
      score: getScoreFromData(scoresByIris, zone.code_iris, selectedIndicator),
    }))
    .sort((a, b) => b.score - a.score)
    .slice(0, 6);

  return (
    <div className="right-panel">
      <h3>Top zones</h3>
      <p className="ranking-subtitle">
        {indicatorLabels[selectedIndicator]} · {selectedYear}
      </p>

      {ranking.map((zone, index) => (
        <div className="rank-row" key={zone.code_iris}>
          <span>{index + 1}</span>
          <strong>{zone.nom_iris}</strong>
          <p>{formatScore(zone.score, selectedIndicator)}</p>
        </div>
      ))}
    </div>
  );
}

export default RankingPanel;