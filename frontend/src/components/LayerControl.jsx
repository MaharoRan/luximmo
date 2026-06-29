import React, { useEffect, useState } from 'react';
import { authFetch } from '../services/scoresService';
import './LayerControl.css';

const API_BASE_URL = "http://127.0.0.1:8000";

function formatTimeRemaining(seconds) {
  if (seconds <= 0) return "En cours...";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export default function LayerControl({ activeLayers, toggleLayer }) {
  const [status, setStatus] = useState(null);
  const [now, setNow] = useState(Math.floor(Date.now() / 1000));

  useEffect(() => {
    const fetchStatus = () => {
      authFetch(`${API_BASE_URL}/api/batch-status`)
        .then(res => res.json())
        .then(data => setStatus(data))
        .catch(err => console.error("Could not fetch batch status", err));
    };

    fetchStatus();

    // Update current time every second
    const clockInterval = setInterval(() => {
      setNow(Math.floor(Date.now() / 1000));
    }, 1000);

    // Sync with backend every 10 seconds
    const syncInterval = setInterval(fetchStatus, 10000);

    return () => {
      clearInterval(clockInterval);
      clearInterval(syncInterval);
    };
  }, []);

  const getRemainingTime = (lastUpdate, intervalSeconds) => {
    if (!status || !lastUpdate) return intervalSeconds;
    const elapsed = now - lastUpdate;
    if (elapsed < 0) return intervalSeconds;
    return intervalSeconds - (elapsed % intervalSeconds);
  };

  return (
    <div className="layer-control">
      <h4>Calques (Temps réel)</h4>
      
      <div className="layer-option-container">
        <label className="layer-option">
          <input 
            type="checkbox" 
            checked={activeLayers.includes('chantiers')}
            onChange={() => toggleLayer('chantiers')}
          />
          <span className="icon">🚧</span> Chantiers en cours
        </label>
        {status && (
          <span className="timer">
            ↻ {formatTimeRemaining(getRemainingTime(status.chantiers_last_update, status.chantiers_interval))}
          </span>
        )}
      </div>

      <div className="layer-option-container">
        <label className="layer-option">
          <input 
            type="checkbox" 
            checked={activeLayers.includes('trafic')}
            onChange={() => toggleLayer('trafic')}
          />
          <span className="icon">🚗</span> Trafic routier
        </label>
        {status && (
          <span className="timer">
            ↻ {formatTimeRemaining(getRemainingTime(status.trafic_last_update, status.trafic_interval))}
          </span>
        )}
      </div>
    </div>
  );
}
