import { useEffect, useRef, useState } from "react";
import {
  fetchAvailableYears,
  fetchArrondissements,
  fetchIrisScores,
  formatEuro,
} from "../services/scoresService";

const indicators = [
  { id: "prix_score", label: "Prix immobilier" },
  { id: "quality", label: "Qualité de vie" },
  { id: "culture", label: "Culture & loisirs" },
  { id: "services", label: "Services publics" },
  { id: "transport", label: "Transports" },
];

const scoreIndicators = indicators.filter((indicator) => indicator.id !== "prix_score");

const indicatorDetails = {
  quality: [
    { key: "q_trees_count", label: "Arbres", unit: "" },
    { key: "q_islands_count", label: "Îlots de fraîcheur", unit: "" },
    { key: "q_islands_equip_count", label: "Îlots équipés", unit: "" },
    { key: "q_sanisettes_count", label: "Sanisettes", unit: "" },
    { key: "q_zones_tourism", label: "Zones touristiques", unit: "" },
  ],
  culture: [
    { key: "c_activities_count", label: "Activités culturelles", unit: "" },
    { key: "c_associations_count", label: "Associations", unit: "" },
    { key: "c_film_locations", label: "Lieux de tournage", unit: "" },
    { key: "c_trees_count", label: "Arbres", unit: "" },
    { key: "c_islands_count", label: "Espaces verts", unit: "" },
    { key: "c_tourism_zones", label: "Zones touristiques", unit: "" },
  ],
  services: [
    { key: "s_hopitaux_count", label: "Hôpitaux", unit: "" },
    { key: "s_ecoles_count", label: "Écoles", unit: "" },
    { key: "s_pharmacies_count", label: "Pharmacies", unit: "" },
    { key: "s_police_count", label: "Commissariats", unit: "" },
    { key: "s_postes_count", label: "Bureaux de poste", unit: "" },
    { key: "s_biblio_count", label: "Bibliothèques", unit: "" },
  ],
  transport: [
    { key: "t_gare_stations", label: "Gares / stations", unit: "" },
    { key: "t_velib_stations", label: "Stations Vélib'", unit: "" },
    { key: "t_velib_capacity", label: "Places Vélib'", unit: "" },
    { key: "t_transport_segments", label: "Voirie", unit: "" },
  ],
  prix_score: [
    { key: "prix_m2_moyen", label: "Prix au m² moyen", unit: "€/m²" },
    { key: "prix_m2_median", label: "Prix au m² médian", unit: "€/m²" },
    { key: "prix_vente_moyen", label: "Prix de vente moyen", unit: "€" },
    { key: "prix_vente_median", label: "Prix de vente médian", unit: "€" },
    { key: "surface_moyenne", label: "Surface moyenne", unit: "m²" },
    { key: "surface_mediane", label: "Surface médiane", unit: "m²" },
    { key: "transactions_count", label: "Nombre de ventes", unit: "" },
  ],
};

function arrLabel(zone) {
  if (!zone) return "Non sélectionné";
  if (zone.nom_iris) return zone.nom_iris;
  return zone.l_ar || `${zone.arrondissement}e Arrondissement`;
}

function getGlobalScore(zone) {
  if (!zone) return null;

  return (
    (zone.quality ?? 50) * 0.2 +
    (zone.culture ?? 50) * 0.2 +
    (zone.services ?? 50) * 0.2 +
    (zone.transport ?? 50) * 0.2 +
    (zone.prix_score ?? 50) * 0.2
  ).toFixed(1);
}

function getCompareClass(valA, valB, lowerIsBetter = false) {
  if (valA == null || valB == null || valA === "—" || valB === "—") return "";

  const numA = Number(valA);
  const numB = Number(valB);

  if (Number.isNaN(numA) || Number.isNaN(numB) || numA === numB) return "";

  if (lowerIsBetter) {
    return numA < numB ? "better-score" : "worse-score";
  }

  return numA > numB ? "better-score" : "worse-score";
}

function formatDetailValue(value, unit) {
  if (value == null) return "–";
  if (unit === "€" || unit === "€/m²") return formatEuro(value) + (unit === "€/m²" ? " / m²" : "");

  if (typeof value === "number") {
    return Number.isInteger(value)
      ? value.toLocaleString("fr-FR") + (unit ? ` ${unit}` : "")
      : value.toFixed(1) + (unit ? ` ${unit}` : "");
  }

  return value + (unit ? ` ${unit}` : "");
}

function ScoreRows({ zone }) {
  if (!zone) return null;

  return (
    <div className="score-list">
      {scoreIndicators.map((indicator) => (
        <p key={indicator.id}>
          {indicator.label}
          <b>{zone[indicator.id] ?? 50} / 100</b>
        </p>
      ))}
    </div>
  );
}

function PrixBlock({ zone }) {
  if (!zone) return null;

  return (
    <div className="prix-block">
      <div className="prix-row">
        <span>Prix au m² moyen</span>
        <b>{formatEuro(zone.prix_m2_moyen)} / m²</b>
      </div>

      <div className="prix-row">
        <span>Prix au m² médian</span>
        <b>{formatEuro(zone.prix_m2_median)} / m²</b>
      </div>

      <div className="prix-row">
        <span>Prix de vente médian</span>
        <b>{formatEuro(zone.prix_vente_median)}</b>
      </div>
    </div>
  );
}

function IndicatorDetails({ zone, indicator }) {
  if (!zone) return null;

  const details = indicatorDetails[indicator];

  if (!details) return null;

  return (
    <div className="detail-block">
      <h4>Détails — {indicators.find((item) => item.id === indicator)?.label}</h4>

      {details.map((detail) => (
        <div className="detail-row" key={detail.key}>
          <span>{detail.label}</span>
          <b>{formatDetailValue(zone[detail.key], detail.unit)}</b>
        </div>
      ))}
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
  const [availableYears, setAvailableYears] = useState([]);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isWaitingForMapClick, setIsWaitingForMapClick] = useState(false);

  const [modalPos, setModalPos] = useState({
    x: window.innerWidth / 2 - 225,
    y: 100,
  });

  const draggingRef = useRef(false);
  const dragOffsetRef = useRef({ x: 0, y: 0 });

  const currentIndicator = indicators.find((item) => item.id === selectedIndicator);

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

    Promise.all([
      fetchArrondissements(selectedYear),
      fetchIrisScores(selectedYear),
    ]).then(([arrData, irisData]) => {
      if (selectedZone) {
        if (selectedZone.code_iris) {
          const freshZone = irisData[selectedZone.code_iris];
          if (freshZone) setSelectedZone(freshZone);
        } else if (selectedZone.arrondissement) {
          const freshZone = arrData[selectedZone.arrondissement];
          if (freshZone) setSelectedZone(freshZone);
        }
      }

      if (compareZone) {
        if (compareZone.code_iris) {
          const freshZone = irisData[compareZone.code_iris];
          if (freshZone) setCompareZone(freshZone);
        } else if (compareZone.arrondissement) {
          const freshZone = arrData[compareZone.arrondissement];
          if (freshZone) setCompareZone(freshZone);
        }
      }
    });
  }, [selectedYear]);

  useEffect(() => {
    if (isWaitingForMapClick) {
      setIsWaitingForMapClick(false);
    }
  }, [
    selectedZone?.arrondissement,
    selectedZone?.code_iris,
    compareZone?.arrondissement,
    compareZone?.code_iris,
  ]);

  const handlePointerDown = (event) => {
    draggingRef.current = true;
    dragOffsetRef.current = {
      x: event.clientX - modalPos.x,
      y: event.clientY - modalPos.y,
    };
    event.target.setPointerCapture(event.pointerId);
  };

  const handlePointerMove = (event) => {
    if (!draggingRef.current) return;

    setModalPos({
      x: event.clientX - dragOffsetRef.current.x,
      y: event.clientY - dragOffsetRef.current.y,
    });
  };

  const handlePointerUp = (event) => {
    draggingRef.current = false;
    event.target.releasePointerCapture(event.pointerId);
  };

  const displayScore = selectedZone
    ? selectedIndicator === "prix_score"
      ? formatEuro(selectedZone.prix_m2_median) + " / m²"
      : `${selectedZone[selectedIndicator] ?? 50} / 100`
    : null;

  const isMismatch =
    selectedZone &&
    compareZone &&
    ((selectedZone.code_iris && !compareZone.code_iris) ||
      (!selectedZone.code_iris && compareZone.code_iris));

  const years = [2021, 2022, 2023, 2024, 2025];

  return (
    <>
      <aside className="sidebar">
        <h1>LUXIMMO</h1>

<<<<<<< Updated upstream
        <div className="card">
          <label>Indicateur</label>
          <select
            value={selectedIndicator}
            onChange={(event) => setSelectedIndicator(event.target.value)}
          >
            {indicators.map((indicator) => (
              <option key={indicator.id} value={indicator.id}>
                {indicator.label}
              </option>
            ))}
          </select>
        </div>

        <div className="card">
          <label style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>Année</span>
            <b>{selectedYear || ""}</b>
          </label>
          {availableYears.length > 0 && (
            <input
              type="range"
              min={Math.min(...availableYears)}
              max={Math.max(...availableYears)}
              step={1}
              value={selectedYear || Math.max(...availableYears)}
              onChange={(event) => setSelectedYear(Number(event.target.value))}
              style={{ width: "100%", marginTop: "10px", cursor: "pointer", accentColor: "#1f6f78" }}
            />
          )}
        </div>

        <button
          className={compareMode ? "compare-btn active" : "compare-btn"}
          onClick={() => {
            setCompareMode(true);
            setIsModalOpen(true);
          }}
=======
      <div className="card">
        <label>Année</label>
        <div style={{ display: 'flex', gap: '4px', marginBottom: '16px' }}>
          {years.map(year => (
            <button
              key={year}
              onClick={() => setSelectedYear(year)}
              style={{
                flex: 1,
                padding: '6px 0',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontWeight: 'bold',
                fontSize: '12px',
                background: selectedYear === year ? '#1f6f78' : '#e5e7eb',
                color: selectedYear === year ? '#ffffff' : '#183247'
              }}
            >
              {year}
            </button>
          ))}
        </div>

        <label>Indicateur</label>
        <select
          value={selectedIndicator}
          onChange={(e) => setSelectedIndicator(e.target.value)}
>>>>>>> Stashed changes
        >
          Comparer des zones
        </button>

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
          <strong>{displayScore || "—"}</strong>
          <span>{selectedZone ? currentIndicator.label : "Score zone"}</span>
        </div>

        {selectedZone ? (
          <div className="zone-card">
            <h3>{arrLabel(selectedZone)}</h3>

            <hr />

            <h4>Score global LuxImmo</h4>
            <strong className="global-score">
              {getGlobalScore(selectedZone)} / 100
            </strong>

            <ScoreRows zone={selectedZone} />

            <hr />

            <h4>Prix immobilier</h4>
            <PrixBlock zone={selectedZone} />

            <hr />

            <IndicatorDetails zone={selectedZone} indicator={selectedIndicator} />
          </div>
        ) : (
          <div className="zone-card">
            <h3>Aucune zone sélectionnée</h3>
            <p>Clique sur un arrondissement ou un IRIS de la carte.</p>
          </div>
        )}
      </aside>

      {isModalOpen && !isWaitingForMapClick && (
        <div
          className="modal-content"
          style={{ left: modalPos.x, top: modalPos.y }}
        >
          <div
            className="modal-header"
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            onPointerCancel={handlePointerUp}
          >
            <h2>Comparer des zones</h2>
          </div>

          <div className="modal-body">
            <div className="target-buttons" style={{ display: "flex", gap: "8px" }}>
              <button
                className={compareTarget === "A" ? "active" : ""}
                onClick={() => {
                  setCompareTarget("A");
                  setIsWaitingForMapClick(true);
                }}
              >
                Cible clic : Zone A
              </button>

              <button
                className={compareTarget === "B" ? "active" : ""}
                onClick={() => {
                  setCompareTarget("B");
                  setIsWaitingForMapClick(true);
                }}
              >
                Cible clic : Zone B
              </button>
            </div>

            <small
              style={{
                display: "block",
                marginTop: "8px",
                marginBottom: "16px",
                color: "#64748b",
              }}
            >
              Cliquez sur un bouton cible puis sélectionnez une zone sur la carte.
            </small>

            {isMismatch && (
              <div
                style={{
                  padding: "12px",
                  background: "#fee2e2",
                  color: "#b91c1c",
                  borderRadius: "6px",
                  marginBottom: "16px",
                  fontSize: "14px",
                  fontWeight: "bold",
                  textAlign: "center",
                }}
              >
                Impossible de comparer un arrondissement avec un quartier IRIS.
              </div>
            )}

            <div className="compare-table">
              <div
                className="compare-row"
                style={{
                  borderBottom: "none",
                  paddingBottom: "16px",
                  alignItems: "stretch",
                }}
              >
                <span />

                <div
                  className="compare-column"
                  style={{
                    margin: 0,
                    padding: "10px",
                    borderRadius: "6px",
                    background: selectedZone ? "#f6f3ee" : "#e5e7eb",
                    color: selectedZone ? "inherit" : "#9ca3af",
                  }}
                >
                  <h4 style={{ margin: 0, fontSize: "13px" }}>
                    {selectedZone ? arrLabel(selectedZone) : "Zone A"}
                  </h4>
                </div>

                <div
                  className="compare-column"
                  style={{
                    margin: 0,
                    padding: "10px",
                    borderRadius: "6px",
                    background: compareZone ? "#f6f3ee" : "#e5e7eb",
                    color: compareZone ? "inherit" : "#9ca3af",
                  }}
                >
                  <h4 style={{ margin: 0, fontSize: "13px" }}>
                    {compareZone ? arrLabel(compareZone) : "Zone B"}
                  </h4>
                </div>
              </div>

              {scoreIndicators.map((indicator) => {
                const valA = selectedZone ? selectedZone[indicator.id] ?? 50 : "—";
                const valB = compareZone ? compareZone[indicator.id] ?? 50 : "—";

                return (
                  <div className="compare-row" key={indicator.id}>
                    <span>{indicator.label}</span>
                    <b className={isMismatch ? "" : getCompareClass(valA, valB)}>
                      {valA}
                    </b>
                    <b className={isMismatch ? "" : getCompareClass(valB, valA)}>
                      {valB}
                    </b>
                  </div>
                );
              })}

              <div className="compare-row">
                <span>Prix au m² moyen</span>
                <b
                  className={
                    isMismatch
                      ? ""
                      : getCompareClass(
                          selectedZone?.prix_m2_moyen,
                          compareZone?.prix_m2_moyen,
                          true
                        )
                  }
                >
                  {selectedZone?.prix_m2_moyen ? formatEuro(selectedZone.prix_m2_moyen) + " / m²" : "—"}
                </b>
                <b
                  className={
                    isMismatch
                      ? ""
                      : getCompareClass(
                          compareZone?.prix_m2_moyen,
                          selectedZone?.prix_m2_moyen,
                          true
                        )
                  }
                >
                  {compareZone?.prix_m2_moyen ? formatEuro(compareZone.prix_m2_moyen) + " / m²" : "—"}
                </b>
              </div>

              <div className="compare-row">
                <span>Prix au m² médian</span>
                <b
                  className={
                    isMismatch
                      ? ""
                      : getCompareClass(
                          selectedZone?.prix_m2_median,
                          compareZone?.prix_m2_median,
                          true
                        )
                  }
                >
                  {selectedZone?.prix_m2_median ? formatEuro(selectedZone.prix_m2_median) + " / m²" : "—"}
                </b>
                <b
                  className={
                    isMismatch
                      ? ""
                      : getCompareClass(
                          compareZone?.prix_m2_median,
                          selectedZone?.prix_m2_median,
                          true
                        )
                  }
                >
                  {compareZone?.prix_m2_median ? formatEuro(compareZone.prix_m2_median) + " / m²" : "—"}
                </b>
              </div>

              <div className="compare-row global">
                <span>Global</span>
                <b
                  className={
                    isMismatch
                      ? ""
                      : getCompareClass(
                          getGlobalScore(selectedZone),
                          getGlobalScore(compareZone)
                        )
                  }
                >
                  {selectedZone ? getGlobalScore(selectedZone) : "—"}
                </b>
                <b
                  className={
                    isMismatch
                      ? ""
                      : getCompareClass(
                          getGlobalScore(compareZone),
                          getGlobalScore(selectedZone)
                        )
                  }
                >
                  {compareZone ? getGlobalScore(compareZone) : "—"}
                </b>
              </div>
            </div>

            <div className="modal-actions">
              <button
                className="cancel-btn"
                onClick={() => {
                  setIsModalOpen(false);
                  setCompareMode(false);
                  setCompareZone(null);
                }}
              >
                Fermer la comparaison
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default Sidebar;