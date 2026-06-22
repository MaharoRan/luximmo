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

  const quality = selectedZone ? getScoreFromData(scoresByIris, selectedZone.code_iris, "quality") : null;
  const culture = selectedZone ? getScoreFromData(scoresByIris, selectedZone.code_iris, "culture") : null;
  const services = selectedZone ? getScoreFromData(scoresByIris, selectedZone.code_iris, "services") : null;
  const transport = selectedZone ? getScoreFromData(scoresByIris, selectedZone.code_iris, "transport") : null;

  const globalScore =
    selectedZone
      ? ((quality * 0.3) + (culture * 0.2) + (services * 0.25) + (transport * 0.25)).toFixed(2)
      : null;

  return (
    <aside className="sidebar">
      <h1>LUXIMMO</h1>

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

        {/* <label>Année</label> 
        <div className="year-row">
          <span>2014</span>
          <input type="range" min="2014" max="2023" defaultValue="2023" />
          <span>2023</span>
        </div>*/}
      </div>

      <div className="kpi-card">
        <strong>{score ? `${score} / 100` : "—"}</strong>
        <span>{selectedZone ? currentIndicator.label : "Score zone"}</span>
      </div>

      {selectedZone ? (
        <div className="zone-card">
          <h3>{selectedZone.nom_iris}</h3>
          <p>Commune : {selectedZone.nom_com}</p>
          <p>Code IRIS : {selectedZone.code_iris}</p>

          <hr />

          <h4>Score global LuxImmo</h4>
          <strong className="global-score">{globalScore} / 100</strong>

          <div className="score-list">
            <p>Qualité de vie <b>{quality} / 100</b></p>
            <p>Culture & loisirs <b>{culture} / 100</b></p>
            <p>Services publics <b>{services} / 100</b></p>
            <p>Transports <b>{transport} / 100</b></p>
          </div>
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