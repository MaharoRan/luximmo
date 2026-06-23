import { useEffect, useState } from "react";
import {
  fetchScores,
  fetchAvailableYears,
  getScoreFromData,
} from "../services/scoresService";

const indicators = [
  { id: "quality", label: "Qualité de vie" },
  { id: "culture", label: "Culture & loisirs" },
  { id: "services", label: "Services publics" },
  { id: "transport", label: "Transports" },
  { id: "price", label: "Prix immobilier" },
];

function formatEuro(value) {
  if (!value) return "—";
  return `${Number(value).toLocaleString("fr-FR")} €`;
}

function getZoneData(scoresByIris, zone) {
  if (!zone) return null;
  return scoresByIris?.[zone.code_iris] ?? null;
}

function getGlobalScore(scoresByIris, zone) {
  if (!zone) return null;

  const quality = getScoreFromData(scoresByIris, zone.code_iris, "quality");
  const culture = getScoreFromData(scoresByIris, zone.code_iris, "culture");
  const services = getScoreFromData(scoresByIris, zone.code_iris, "services");
  const transport = getScoreFromData(scoresByIris, zone.code_iris, "transport");

  return (
    quality * 0.3 +
    culture * 0.2 +
    services * 0.25 +
    transport * 0.25
  ).toFixed(2);
}

function ScoreRows({ scoresByIris, zone }) {
  if (!zone) return null;

  return (
    <div className="score-list">
      <p>Qualité de vie <b>{getScoreFromData(scoresByIris, zone.code_iris, "quality")} / 100</b></p>
      <p>Culture & loisirs <b>{getScoreFromData(scoresByIris, zone.code_iris, "culture")} / 100</b></p>
      <p>Services publics <b>{getScoreFromData(scoresByIris, zone.code_iris, "services")} / 100</b></p>
      <p>Transports <b>{getScoreFromData(scoresByIris, zone.code_iris, "transport")} / 100</b></p>
    </div>
  );
}

function PriceBlock({ scoresByIris, zone }) {
  const zoneData = getZoneData(scoresByIris, zone);
  if (!zoneData) return null;

  return (
    <div className="price-block">
      <h4>Marché immobilier</h4>
      <p>Prix médian <b>{formatEuro(zoneData.prix_m2_median)} / m²</b></p>
      <p>Prix moyen <b>{formatEuro(zoneData.prix_m2_mean)} / m²</b></p>
      <p>Transactions <b>{zoneData.transactions_count || "—"}</b></p>
      <p>Année <b>{zoneData.year || "—"}</b></p>
    </div>
  );
}

function Sidebar({
  selectedIndicator,
  setSelectedIndicator,
  selectedYear,
  setSelectedYear,
  selectedZone,
  compareZone,
  compareMode,
  setCompareMode,
  compareTarget,
  setCompareTarget,
  setSelectedZone,
  setCompareZone,
}) {
  const [scoresByIris, setScoresByIris] = useState({});
  const [availableYears, setAvailableYears] = useState([]);

  useEffect(() => {
    fetchAvailableYears().then((years) => {
      setAvailableYears(years);
      if (!selectedYear && years.length > 0) {
        setSelectedYear(years[years.length - 1]);
      }
    });
  }, []);

  useEffect(() => {
    if (!selectedYear) return;
    fetchScores(selectedYear).then(setScoresByIris);
  }, [selectedYear]);

  const currentIndicator = indicators.find((i) => i.id === selectedIndicator);

  const score = selectedZone
    ? getScoreFromData(scoresByIris, selectedZone.code_iris, selectedIndicator)
    : null;

  const selectedZoneData = getZoneData(scoresByIris, selectedZone);
  const compareZoneData = getZoneData(scoresByIris, compareZone);

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
      </div>

      <div className="card">
        <label>Année</label>
        <select
          value={selectedYear || ""}
          onChange={(e) => setSelectedYear(Number(e.target.value))}
        >
          {availableYears.map((year) => (
            <option key={year} value={year}>
              {year}
            </option>
          ))}
        </select>
      </div>

      <button
        className={compareMode ? "compare-btn active" : "compare-btn"}
        onClick={() => setCompareMode(!compareMode)}
      >
        {compareMode ? "Mode comparaison activé" : "Activer comparaison"}
      </button>

      {compareMode && (
        <div className="compare-target">
          <p>Sélection à modifier :</p>
          <div className="target-buttons">
            <button
              className={compareTarget === "A" ? "active" : ""}
              onClick={() => setCompareTarget("A")}
            >
              Zone A
            </button>
            <button
              className={compareTarget === "B" ? "active" : ""}
              onClick={() => setCompareTarget("B")}
            >
              Zone B
            </button>
          </div>
          <small>Clique sur la carte pour choisir la zone sélectionnée.</small>
        </div>
      )}

      <button
        className="reset-btn"
        onClick={() => {
          setSelectedZone(null);
          setCompareZone(null);
        }}
      >
        Réinitialiser
      </button>

      <div className="kpi-card">
        <strong>
          {score
            ? selectedIndicator === "price"
              ? `${Number(score).toLocaleString("fr-FR")} €/m²`
              : `${score} / 100`
            : "—"}
        </strong>
        <span>{selectedZone ? currentIndicator.label : "Score zone"}</span>
      </div>

      {selectedZone ? (
        <div className="zone-card">
          <h3>{selectedZone.nom_iris}</h3>
          <p>Commune : {selectedZone.nom_com}</p>
          <p>Code IRIS : {selectedZone.code_iris}</p>

          <hr />
          <PriceBlock scoresByIris={scoresByIris} zone={selectedZone} />

          <hr />
          <h4>Score global LuxImmo</h4>
          <strong className="global-score">
            {getGlobalScore(scoresByIris, selectedZone)} / 100
          </strong>

          <ScoreRows scoresByIris={scoresByIris} zone={selectedZone} />
        </div>
      ) : (
        <div className="zone-card">
          <h3>Aucune zone sélectionnée</h3>
          <p>Clique sur une zone IRIS de la carte.</p>
        </div>
      )}

      {compareMode && (
        <div className="compare-card">
          <h3>Comparaison</h3>

          <div className="compare-column">
            <h4>Zone A</h4>
            <p>{selectedZone ? selectedZone.nom_iris : "Non sélectionnée"}</p>
          </div>

          <div className="compare-column">
            <h4>Zone B</h4>
            <p>{compareZone ? compareZone.nom_iris : "Non sélectionnée"}</p>
          </div>

          {selectedZone && compareZone && (
            <div className="compare-table">
              {indicators
                .filter((indicator) => indicator.id !== "price")
                .map((indicator) => (
                  <div className="compare-row" key={indicator.id}>
                    <span>{indicator.label}</span>
                    <b>{getScoreFromData(scoresByIris, selectedZone.code_iris, indicator.id)}</b>
                    <b>{getScoreFromData(scoresByIris, compareZone.code_iris, indicator.id)}</b>
                  </div>
                ))}

              <div className="compare-row global">
                <span>Global</span>
                <b>{getGlobalScore(scoresByIris, selectedZone)}</b>
                <b>{getGlobalScore(scoresByIris, compareZone)}</b>
              </div>

              <div className="compare-row">
                <span>Prix médian €/m²</span>
                <b>{formatEuro(selectedZoneData?.prix_m2_median)}</b>
                <b>{formatEuro(compareZoneData?.prix_m2_median)}</b>
              </div>

              <div className="compare-row">
                <span>Transactions</span>
                <b>{selectedZoneData?.transactions_count || "—"}</b>
                <b>{compareZoneData?.transactions_count || "—"}</b>
              </div>
            </div>
          )}
        </div>
      )}
    </aside>
  );
}

export default Sidebar;