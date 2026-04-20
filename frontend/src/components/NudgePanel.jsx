/**
 * NudgePanel — fetches /nudges/generate every 60 s.
 * Displays 2–3 nudges with urgency colour coding and slide-in animation.
 */

import { useCallback, useEffect, useRef, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const URGENCY_CONFIG = {
  low:    { color: "#1D9E75", bg: "rgba(29,158,117,0.12)", label: "LOW",    icon: "✅" },
  medium: { color: "#EF9F27", bg: "rgba(239,159,39,0.12)", label: "MED",    icon: "⚠️" },
  high:   { color: "#E24B4A", bg: "rgba(226,75,74,0.12)",  label: "HIGH",   icon: "🚨" },
};

function NudgeCard({ nudge, index }) {
  const cfg = URGENCY_CONFIG[nudge.urgency] || URGENCY_CONFIG.low;
  return (
    <div
      className="nudge-card"
      style={{
        animationDelay: `${index * 80}ms`,
        background: cfg.bg,
        borderLeft: `3px solid ${cfg.color}`,
      }}
    >
      <div className="nudge-header">
        <span className="nudge-icon">{cfg.icon}</span>
        <span className="nudge-zone" style={{ color: cfg.color }}>
          {nudge.zone}
        </span>
        <span
          className="nudge-badge"
          style={{ background: cfg.color }}
        >
          {cfg.label}
        </span>
      </div>
      <p className="nudge-message">{nudge.message}</p>
    </div>
  );
}

export default function NudgePanel() {
  const [nudges, setNudges]     = useState([]);
  const [loading, setLoading]   = useState(false);
  const [lastFetch, setLastFetch] = useState(null);
  const intervalRef = useRef(null);

  const fetchNudges = useCallback(async () => {
    setLoading(true);
    try {
      const res  = await fetch(`${API_URL}/nudges/generate`, { method: "POST" });
      const data = await res.json();
      setNudges(data.nudges || []);
      setLastFetch(new Date());
    } catch (err) {
      console.error("[NudgePanel] fetch error", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchNudges();
    intervalRef.current = setInterval(fetchNudges, 60_000);
    return () => clearInterval(intervalRef.current);
  }, [fetchNudges]);

  return (
    <div className="nudge-panel" role="region" aria-live="polite" aria-label="Live crowd nudges and recommendations">
      <div className="nudge-panel-header">
        <div className="nudge-title-row">
          <span className="nudge-title-icon">🧠</span>
          <h2 className="nudge-title">Live Nudges</h2>
          {loading && <div className="nudge-spinner" />}
        </div>
        <div className="nudge-meta">
          {lastFetch && (
            <span className="nudge-timestamp">
              Updated {lastFetch.toLocaleTimeString()}
            </span>
          )}
          <button
            className="nudge-refresh-btn"
            onClick={fetchNudges}
            disabled={loading}
            title="Refresh nudges"
          >
            ↻
          </button>
        </div>
      </div>

      {nudges.length === 0 && !loading && (
        <p className="nudge-empty">No nudges needed right now — all zones balanced.</p>
      )}

      <div className="nudge-list">
        {nudges.map((nudge, i) => (
          <NudgeCard key={`${nudge.zone}-${i}`} nudge={nudge} index={i} />
        ))}
      </div>
    </div>
  );
}
