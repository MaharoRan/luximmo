import { useEffect, useState } from "react";
import { fetchArrondissements, formatEuro } from "../services/scoresService";

const indicatorLabels = {
  quality: "Qualité de vie",
  culture: "Culture & loisirs",
  services: "Services publics",
  transport: "Transports",
  prix_score: "Prix immobilier",
};

function RankingPanel({ selectedIndicator, selectedYear }) {
  const [arrData, setArrData] = useState({});

  useEffect(() => {
    fetchArrondissements(selectedYear).then(setArrData);
  }, [selectedYear]);

  const isPrix = selectedIndicator === "prix_score";

  const ranking = Object.values(arrData)
    .map((arr) => ({
      key: arr.arrondissement,
      label: `${arr.arrondissement}e Ardt`,
      score: arr[selectedIndicator] ?? 50,
      loyer_median: arr.loyer_median,
    }))
    .sort((a, b) =>
      isPrix ? a.loyer_median - b.loyer_median : b.score - a.score
    )
    .slice(0, 6);

  return (
    <div className="right-panel">
      <h3>Top arrondissements</h3>

      <p className="ranking-subtitle">
        {indicatorLabels[selectedIndicator]}
        {selectedYear ? ` · ${selectedYear}` : ""}
      </p>

      {ranking.map((item, index) => (
        <div className="rank-row" key={item.key}>
          <span>{index + 1}</span>
          <strong>{item.label}</strong>
          <p>{isPrix ? formatEuro(item.loyer_median) : `${item.score}/100`}</p>
        </div>
      ))}
    </div>
  );
}

export default RankingPanel;