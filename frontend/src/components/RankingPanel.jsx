import { useEffect, useState } from "react";
import { fetchScores } from "../services/scoresService";

const indicatorLabels = {
  quality: "Qualité de vie",
  culture: "Culture & loisirs",
  services: "Services publics",
  transport: "Transports",
};

function RankingPanel({ selectedIndicator }) {
  const [scoresByIris, setScoresByIris] = useState({});

  useEffect(() => {
    fetchScores().then(setScoresByIris);
  }, []);

  const ranking = Object.values(scoresByIris)
    .map((zone) => ({
      code_iris: zone.code_iris,
      nom_iris: zone.nom_iris || zone.code_iris,
      score: zone[selectedIndicator] ?? 50,
    }))
    .sort((a, b) => b.score - a.score)
    .slice(0, 6);

  return (
    <div className="right-panel">
      <h3>Top zones</h3>
      <p className="ranking-subtitle">{indicatorLabels[selectedIndicator]}</p>

      {ranking.map((zone, index) => (
        <div className="rank-row" key={zone.code_iris}>
          <span>{index + 1}</span>
          <strong>{zone.nom_iris}</strong>
          <p>{zone.score}/100</p>
        </div>
      ))}
    </div>
  );
}

export default RankingPanel;