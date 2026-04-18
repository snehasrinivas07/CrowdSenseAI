/**
 * AdminDashboard — Table of all 14 zones with LLM staff actions.
 * "Simulate Event" buttons, top-bar stats, per-row trend arrows.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useCrowdStream } from "../hooks/useCrowdStream";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const EVENT_BUTTONS = ["PRE_GAME", "IN_PLAY", "HALF_TIME", "FULL_TIME"];

const EVENT_LABELS = {
  PRE_GAME:  { label: "Pre-Game",  emoji: "🏟️" },
  IN_PLAY:   { label: "In Play",   emoji: "⚽" },
  HALF_TIME: { label: "Half-Time", emoji: "🔔" },
  FULL_TIME: { label: "Full-Time", emoji: "🏁" },
};

function densityColor(density) {
  if (density < 40)  return "#1D9E75";
  if (density <= 70) return "#EF9F27";
  return "#E24B4A";
}

function TrendArrow({ trend }) {
  if (trend === "rising")  return <span style={{ color: "#E24B4A" }}>▲</span>;
  if (trend === "falling") return <span style={{ color: "#1D9E75" }}>▼</span>;
  return <span style={{ color: "#64748b" }}>●</span>;
}

function DensityBar({ density }) {
  const color = densityColor(density);
  return (
    <div className="density-bar-bg">
      <div
        className="density-bar-fill"
        style={{
          width: `${Math.round(density)}%`,
          background: color,
          transition: "width 0.6s ease",
        }}
      />
    </div>
  );
}

export default function AdminDashboard() {
  const { zones, event, summary, connected, triggerEvent } = useCrowdStream();
  const [staffActions, setStaffActions] = useState({});
  const [loadingActions, setLoadingActions] = useState(false);
  const [activeEvent, setActiveEvent] = useState(null);
  const pollRef = useRef(null);

  const fetchStaffActions = useCallback(async () => {
    setLoadingActions(true);
    try {
      const res  = await fetch(`${API_URL}/admin/staff-actions`);
      const data = await res.json();
      setStaffActions(data.actions || {});
    } catch (err) {
      console.error("[AdminDashboard] staff actions error", err);
    } finally {
      setLoadingActions(false);
    }
  }, []);

  // Fetch staff actions on mount and every 30 s
  useEffect(() => {
    fetchStaffActions();
    pollRef.current = setInterval(fetchStaffActions, 30_000);
    return () => clearInterval(pollRef.current);
  }, [fetchStaffActions]);

  const handleTrigger = async (ev) => {
    setActiveEvent(ev);
    await triggerEvent(ev);
    // Refresh staff actions after event changes crowd state
    setTimeout(fetchStaffActions, 2000);
  };

  const eventInfo = EVENT_LABELS[event] || { label: event, emoji: "📡" };

  return (
    <div className="admin-dashboard">
      {/* ── Top bar ── */}
      <header className="admin-header">
        <div className="admin-header-left">
          <div className="admin-logo">
            <span className="admin-logo-icon">🏟️</span>
            <span className="admin-logo-text">CrowdSense</span>
            <span className="admin-logo-sub">Admin</span>
          </div>
          <div className={`admin-ws-badge ${connected ? "connected" : "disconnected"}`}>
            {connected ? "● LIVE" : "○ Reconnecting…"}
          </div>
        </div>

        <div className="admin-stats-row">
          {summary && (
            <>
              <div className="admin-stat">
                <div className="admin-stat-value">{summary.total_crowd_pct}%</div>
                <div className="admin-stat-label">Avg Density</div>
              </div>
              <div className="admin-stat">
                <div className="admin-stat-value" style={{ color: "#E24B4A" }}>
                  {summary.highest_risk_zone}
                </div>
                <div className="admin-stat-label">Highest Risk</div>
              </div>
              <div className="admin-stat">
                <div className="admin-stat-value">{summary.avg_wait_minutes} min</div>
                <div className="admin-stat-label">Avg Wait</div>
              </div>
            </>
          )}
          <div className="admin-stat">
            <div className="admin-stat-value">{eventInfo.emoji} {eventInfo.label}</div>
            <div className="admin-stat-label">Current Phase</div>
          </div>
        </div>
      </header>

      {/* ── Event triggers ── */}
      <section className="admin-events">
        <span className="admin-events-label">Simulate Event:</span>
        {EVENT_BUTTONS.map((ev) => {
          const info = EVENT_LABELS[ev];
          return (
            <button
              key={ev}
              className={`event-btn ${event === ev ? "active" : ""}`}
              onClick={() => handleTrigger(ev)}
            >
              {info.emoji} {info.label}
            </button>
          );
        })}
        <button
          className="event-btn refresh-btn"
          onClick={fetchStaffActions}
          disabled={loadingActions}
          title="Refresh staff actions"
        >
          {loadingActions ? "⟳" : "↻"} Refresh Actions
        </button>
      </section>

      {/* ── Zone table ── */}
      <div className="admin-table-wrapper">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Zone</th>
              <th>Type</th>
              <th>Density</th>
              <th>Bar</th>
              <th>Trend</th>
              <th>Wait</th>
              <th>Staff Action</th>
            </tr>
          </thead>
          <tbody>
            {zones.map((zone) => {
              const color  = densityColor(zone.density);
              const action = staffActions[zone.id] || (loadingActions ? "Loading…" : "—");
              return (
                <tr key={zone.id} className="admin-row">
                  <td>
                    <span className="zone-name">{zone.name}</span>
                  </td>
                  <td>
                    <span className="zone-type-badge">{zone.type}</span>
                  </td>
                  <td>
                    <span style={{ color, fontWeight: 700 }}>
                      {Math.round(zone.density)}%
                    </span>
                  </td>
                  <td style={{ minWidth: 100 }}>
                    <DensityBar density={zone.density} />
                  </td>
                  <td>
                    <TrendArrow trend={zone.trend} />
                    <span className="trend-label"> {zone.trend}</span>
                  </td>
                  <td>
                    <span className="wait-badge">{zone.wait_minutes} min</span>
                  </td>
                  <td className="staff-action-cell">
                    {action}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
