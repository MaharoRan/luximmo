import React from 'react';
import './LayerControl.css';

export default function LayerControl({ activeLayers, toggleLayer }) {
  return (
    <div className="layer-control">
      <h4>Calques (Temps réel)</h4>
      <label className="layer-option">
        <input 
          type="checkbox" 
          checked={activeLayers.includes('chantiers')}
          onChange={() => toggleLayer('chantiers')}
        />
        <span className="icon">🚧</span> Chantiers en cours
      </label>
      <label className="layer-option">
        <input 
          type="checkbox" 
          checked={activeLayers.includes('trafic')}
          onChange={() => toggleLayer('trafic')}
        />
        <span className="icon">🚗</span> Trafic routier
      </label>
    </div>
  );
}
