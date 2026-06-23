import { useEffect, useState, useRef } from "react";
import { formatEuro } from "../services/scoresService";

const indicators = [
  { id: "prix_score", label: "Prix immobilier" },
  { id: "quality", label: "Qualité de vie" },
  { id: "culture", label: "Culture & loisirs" },
  { id: "services", label: "Services publics" },
  { id: "transport", label: "Transports" },
];

const scoreIndicators = indicators.filter((i) => i.id !== "prix_score");

const getCompareClass = (valA, valB, lowerIsBetter = false) => {
  if (valA == null || valB == null || valA === "—" || valB === "—") return "";
  const numA = Number(valA);
  const numB = Number(valB);
  if (isNaN(numA) || isNaN(numB) || numA === numB) return "";
  
  if (lowerIsBetter) {
    return numA < numB ? "better-score" : "worse-score";
  }
  return numA > numB ? "better-score" : "worse-score";
};

/* ── Détails par indicateur (clé API préfixée → label FR) ── */
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
    { key: "t_transport_segments", label: "Voirie (Bus, Métro, Commerces)", unit: "" },
  ],
  prix_score: [
    { key: "loyer_moyen", label: "Prix moyen", unit: "€" },
    { key: "loyer_median", label: "Prix médian", unit: "€" },
    { key: "loyer_maximum", label: "Prix maximum", unit: "€" },
  ],
};

function getGlobalScore(zone) {
  if (!zone) return null;
  return (
    (zone.quality ?? 50) * 0.20 +
    (zone.culture ?? 50) * 0.20 +
    (zone.services ?? 50) * 0.20 +
    (zone.transport ?? 50) * 0.20 +
    (zone.prix_score ?? 50) * 0.20
  ).toFixed(1);
}

function arrLabel(zone) {
  if (!zone) return "Non sélectionné";
  if (zone.nom_iris) return zone.nom_iris;
  return zone.l_ar || `${zone.arrondissement}e Arrondissement`;
}

function formatDetailValue(value, unit) {
  if (value == null) return "–";
  if (unit === "€") return formatEuro(value);
  if (typeof value === "number") {
    return Number.isInteger(value) ? value.toLocaleString("fr-FR") : value.toFixed(1);
  }
  return value;
}

function IndicatorDetails({ zone, indicator }) {
  if (!zone) return null;

  const details = indicatorDetails[indicator];
  if (!details) return null;

  return (
    <div className="detail-block">
      <h4>Détails — {indicators.find((i) => i.id === indicator)?.label}</h4>
      {details.map((d) => (
        <div className="detail-row" key={d.key}>
          <span>{d.label}</span>
          <b>{formatDetailValue(zone[d.key], d.unit)}</b>
        </div>
      ))}
    </div>
  );
}

function ScoreRows({ zone }) {
  if (!zone) return null;
  return (
    <div className="score-list">
      {scoreIndicators.map((ind) => (
        <p key={ind.id}>
          {ind.label} <b>{zone[ind.id] ?? 50} / 100</b>
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
        <span>Prix moyen</span>
        <b>{formatEuro(zone.loyer_moyen)}</b>
      </div>
      <div className="prix-row">
        <span>Prix médian</span>
        <b>{formatEuro(zone.loyer_median)}</b>
      </div>
      <div className="prix-row">
        <span>Prix maximum</span>
        <b>{formatEuro(zone.loyer_maximum)}</b>
      </div>
    </div>
  );
}

function Sidebar({
  selectedIndicator,
  setSelectedIndicator,
  selectedZone,
  compareZone,
  compareMode,
  setCompareMode,
  compareTarget,
  setCompareTarget,
  setSelectedZone,
  setCompareZone,
}) {
  const currentIndicator = indicators.find((i) => i.id === selectedIndicator);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isWaitingForMapClick, setIsWaitingForMapClick] = useState(false);
  
  // Dragging state
  const [modalPos, setModalPos] = useState({ x: window.innerWidth / 2 - 225, y: 100 });
  const draggingRef = useRef(false);
  const dragOffsetRef = useRef({ x: 0, y: 0 });

  useEffect(() => {
    if (isWaitingForMapClick) {
      setIsWaitingForMapClick(false);
    }
  }, [selectedZone?.arrondissement, compareZone?.arrondissement]);

  const handlePointerDown = (e) => {
    draggingRef.current = true;
    dragOffsetRef.current = {
      x: e.clientX - modalPos.x,
      y: e.clientY - modalPos.y
    };
    e.target.setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e) => {
    if (!draggingRef.current) return;
    setModalPos({
      x: e.clientX - dragOffsetRef.current.x,
      y: e.clientY - dragOffsetRef.current.y
    });
  };

  const handlePointerUp = (e) => {
    draggingRef.current = false;
    e.target.releasePointerCapture(e.pointerId);
  };

  const displayScore = selectedZone
    ? selectedIndicator === "prix_score"
      ? formatEuro(selectedZone.loyer_moyen)
      : `${selectedZone[selectedIndicator] ?? 50} / 100`
    : null;

  const isMismatch = selectedZone && compareZone && (
    (selectedZone.code_iris && !compareZone.code_iris) || 
    (!selectedZone.code_iris && compareZone.code_iris)
  );

  return (
    <>
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

      <button
        className={compareMode ? "compare-btn active" : "compare-btn"}
        onClick={() => {
          setCompareMode(true);
          setIsModalOpen(true);
        }}
      >
        Comparer des arrondissements
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
        <span>{selectedZone ? currentIndicator.label : "Score arrondissement"}</span>
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
          <h3>Aucun arrondissement sélectionné</h3>
          <p>Clique sur un arrondissement de la carte.</p>
        </div>
      )}

      {/* The compare mode is completely in the modal now */}
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
          <h2>Comparer des arrondissements</h2>
        </div>

        <div className="modal-body">
          <div className="target-buttons" style={{ display: 'flex', gap: '8px' }}>
            <button
              className={compareTarget === "A" ? "active" : ""}
              onClick={() => { setCompareTarget("A"); setIsWaitingForMapClick(true); }}
              style={{ flex: 1, padding: '10px', borderRadius: '6px', border: 'none', cursor: 'pointer', background: compareTarget === "A" ? "#1f6f78" : "#e5e7eb", color: compareTarget === "A" ? "white" : "#183247", fontWeight: 'bold' }}
            >
              Cible clic: Zone A
            </button>
            <button
              className={compareTarget === "B" ? "active" : ""}
              onClick={() => { setCompareTarget("B"); setIsWaitingForMapClick(true); }}
              style={{ flex: 1, padding: '10px', borderRadius: '6px', border: 'none', cursor: 'pointer', background: compareTarget === "B" ? "#1f6f78" : "#e5e7eb", color: compareTarget === "B" ? "white" : "#183247", fontWeight: 'bold' }}
            >
              Cible clic: Zone B
            </button>
          </div>
          <small style={{display: 'block', marginTop: '8px', marginBottom: '16px', color: '#64748b'}}>
            Cliquez sur un bouton cible puis sélectionnez un arrondissement sur la carte.
          </small>

          <div className="compare-table" style={{marginTop: '20px', borderTop: '1px solid #e5e7eb', paddingTop: '16px'}}>
            <div className="compare-row" style={{ borderBottom: 'none', paddingBottom: '16px', alignItems: 'stretch' }}>
              <span />
              <div 
                className="compare-column" 
                style={{ margin: 0, padding: '10px', borderRadius: '6px', background: selectedZone ? '#f6f3ee' : '#e5e7eb', color: selectedZone ? 'inherit' : '#9ca3af' }}
              >
                <h4 style={{margin: '0', fontSize: '13px'}}>{selectedZone ? arrLabel(selectedZone) : 'Zone A'}</h4>
              </div>
              <div 
                className="compare-column" 
                style={{ margin: 0, padding: '10px', borderRadius: '6px', background: compareZone ? '#f6f3ee' : '#e5e7eb', color: compareZone ? 'inherit' : '#9ca3af' }}
              >
                <h4 style={{margin: '0', fontSize: '13px'}}>{compareZone ? arrLabel(compareZone) : 'Zone B'}</h4>
              </div>
            </div>

            {isMismatch && (
              <div style={{ padding: '12px', background: '#fee2e2', color: '#b91c1c', borderRadius: '6px', marginBottom: '16px', fontSize: '14px', fontWeight: 'bold', textAlign: 'center' }}>
                Impossible de comparer un arrondissement avec un quartier IRIS.
              </div>
            )}

            {scoreIndicators.map((indicator) => {
              const valA = selectedZone ? (selectedZone[indicator.id] ?? 50) : "—";
              const valB = compareZone ? (compareZone[indicator.id] ?? 50) : "—";
              return (
                <div className="compare-row" key={indicator.id}>
                  <span>{indicator.label}</span>
                  <b className={isMismatch ? "" : getCompareClass(valA, valB)}>{valA}</b>
                  <b className={isMismatch ? "" : getCompareClass(valB, valA)}>{valB}</b>
                </div>
              );
            })}

            <div className="compare-row">
              <span>Prix moyen</span>
              <b className={isMismatch ? "" : getCompareClass(selectedZone?.loyer_moyen, compareZone?.loyer_moyen, true)}>{selectedZone ? formatEuro(selectedZone.loyer_moyen) : "—"}</b>
              <b className={isMismatch ? "" : getCompareClass(compareZone?.loyer_moyen, selectedZone?.loyer_moyen, true)}>{compareZone ? formatEuro(compareZone.loyer_moyen) : "—"}</b>
            </div>

            <div className="compare-row">
              <span>Prix médian</span>
              <b className={isMismatch ? "" : getCompareClass(selectedZone?.loyer_median, compareZone?.loyer_median, true)}>{selectedZone ? formatEuro(selectedZone.loyer_median) : "—"}</b>
              <b className={isMismatch ? "" : getCompareClass(compareZone?.loyer_median, selectedZone?.loyer_median, true)}>{compareZone ? formatEuro(compareZone.loyer_median) : "—"}</b>
            </div>

            <div className="compare-row global">
              <span>Global</span>
              <b className={isMismatch ? "" : getCompareClass(getGlobalScore(selectedZone), getGlobalScore(compareZone))}>{selectedZone ? getGlobalScore(selectedZone) : "—"}</b>
              <b className={isMismatch ? "" : getCompareClass(getGlobalScore(compareZone), getGlobalScore(selectedZone))}>{compareZone ? getGlobalScore(compareZone) : "—"}</b>
            </div>
          </div>
          
          <div className="modal-actions">
            <button className="cancel-btn" onClick={() => setIsModalOpen(false)}>Fermer la comparaison</button>
          </div>
        </div>
      </div>
    )}
    </>
  );
}

export default Sidebar;