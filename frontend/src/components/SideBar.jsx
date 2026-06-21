import { useEffect, useState } from "react";
import { fetchScores, getScoreFromData } from "../services/scoresService";

const indicators = [
  { id: "quality", label: "Qualité de vie" },
  { id: "culture", label: "Culture & loisirs" },
  { id: "services", label: "Services publics" },
  { id: "transport", label: "Transports" },
];

function Sidebar({ selectedIndicator, setSelectedIndicator, selectedZone }) {
  const [scoresByIris, setScoresByIris] = useState({});

  useEffect(() => {
    fetchScores().then(setScoresByIris);
  }, []);

  const currentIndicator = indicators.find((i) => i.id === selectedIndicator);

  const score = selectedZone
    ? getScoreFromData(scoresByIris, selectedZone.code_iris, selectedIndicator)
    : null;

  return (
    <aside className="sidebar">
      <h1>URBAN DATA EXPLORER</h1>

      <div className="card">
        <label>Indicateur</label>
        <select
          value={selectedIndicator}
          onChange={(e) => setSelectedIndicator(e.target.value)}
        >
          {indicators.map((indicator) => (
            <option key={indicator.id} value={indicator.id}>
              {indicator.label}
            </option>
          ))}
        </select>

        <label>Année</label>
        <div className="year-row">
          <span>2014</span>
          <input type="range" min="2014" max="2023" defaultValue="2023" />
          <span>2023</span>
        </div>
      </div>

      <div className="kpi-card">
        <strong>{score ? `${score} / 100` : "—"}</strong>
        <span>{selectedZone ? currentIndicator.label : "Score zone"}</span>
      </div>

      <div className="kpi-card">
        <strong>9 400 €</strong>
        <span>Prix/m² médian</span>
      </div>

      <div className="legend">
        <div className="legend-gradient"></div>
        <div className="legend-labels">
          <span>Faible</span>
          <span>Moyen</span>
          <span>Élevé</span>
        </div>
      </div>

      {selectedZone ? (
        <div className="zone-card">
          <h3>{selectedZone.nom_iris}</h3>
          <p>Code IRIS : {selectedZone.code_iris}</p>
          <p>Commune : {selectedZone.nom_com}</p>
          <p>Indicateur : {currentIndicator.label}</p>
          <p>Score : {score} / 100</p>
        </div>
      ) : (
        <div className="zone-card">
          <h3>Aucune zone sélectionnée</h3>
          <p>Clique sur une zone IRIS de la carte.</p>
        </div>
      )}
    </aside>
  );
}

export default Sidebar;