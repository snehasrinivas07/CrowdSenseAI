/**
 * CrowdSense AI — Root Application
 * Route /       → Attendee view  (StadiumMap + NudgePanel + CrowdChat)
 * Route /admin  → Admin Dashboard
 */

import { useState } from "react";
import { BrowserRouter, Link, Route, Routes, useLocation } from "react-router-dom";

import AdminDashboard from "./components/AdminDashboard";
import CrowdChat from "./components/CrowdChat";
import NudgePanel from "./components/NudgePanel";
import StadiumMap from "./components/StadiumMap";
import { useCrowdStream } from "./hooks/useCrowdStream";

// ─── Top Navigation Bar ───────────────────────────────────────────────────

function NavBar({ connected, event }) {
  const loc = useLocation();
  const isAdmin = loc.pathname === "/admin";

  const EVENT_COLORS = {
    PRE_GAME:  "#a78bfa",
    IN_PLAY:   "#1D9E75",
    HALF_TIME: "#EF9F27",
    FULL_TIME: "#E24B4A",
  };

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <span className="navbar-icon">🏟️</span>
        <span className="navbar-title">CrowdSense</span>
        <span className="navbar-subtitle">AI</span>
      </div>

      <div className="navbar-center">
        <div
          className="event-pill"
          style={{ borderColor: EVENT_COLORS[event] || "#64748b", color: EVENT_COLORS[event] }}
        >
          {event?.replace("_", " ")}
        </div>
      </div>

      <div className="navbar-right">
        <div className={`ws-indicator ${connected ? "live" : "offline"}`}>
          <span className="ws-dot" />
          {connected ? "LIVE" : "Reconnecting…"}
        </div>

        <div className="nav-links">
          <Link to="/"      className={`nav-link ${!isAdmin ? "active" : ""}`}>Attendee</Link>
          <Link to="/admin" className={`nav-link ${isAdmin  ? "active" : ""}`}>Admin</Link>
        </div>
      </div>
    </nav>
  );
}

// ─── Attendee View ────────────────────────────────────────────────────────

function AttendeeView() {
  const { zones, event, summary, connected, triggerEvent } = useCrowdStream();
  const [highlightedZones, setHighlightedZones] = useState([]);

  return (
    <div className="attendee-layout">
      {/* Left column: stadium map + summary strip */}
      <div className="attendee-left">
        {/* Summary strip */}
        {summary && (
          <div className="summary-strip">
            <div className="summary-stat">
              <span className="summary-stat-value">{summary.total_crowd_pct}%</span>
              <span className="summary-stat-label">Avg Density</span>
            </div>
            <div className="summary-divider" />
            <div className="summary-stat">
              <span className="summary-stat-value waiting">{summary.avg_wait_minutes} min</span>
              <span className="summary-stat-label">Avg Wait</span>
            </div>
            <div className="summary-divider" />
            <div className="summary-stat">
              <span className="summary-stat-value risk">{summary.highest_risk_zone}</span>
              <span className="summary-stat-label">Busiest Zone</span>
            </div>
          </div>
        )}

        <div className="map-container">
          <StadiumMap zones={zones} highlightedZones={highlightedZones} />
        </div>

        {/* Legend */}
        <div className="map-legend">
          <span className="legend-item"><span className="legend-dot" style={{ background: "#1D9E75" }} />Low (&lt;40%)</span>
          <span className="legend-item"><span className="legend-dot" style={{ background: "#EF9F27" }} />Medium (40–70%)</span>
          <span className="legend-item"><span className="legend-dot" style={{ background: "#E24B4A" }} />High (&gt;70%)</span>
        </div>
      </div>

      {/* Right column: nudges + chat */}
      <div className="attendee-right">
        <NudgePanel />
        <CrowdChat onZoneHighlight={setHighlightedZones} />
      </div>
    </div>
  );
}

// ─── App Shell with router ────────────────────────────────────────────────

function AppShell() {
  const { zones, event, summary, connected, triggerEvent } = useCrowdStream();

  return (
    <div className="app-shell">
      <NavBar connected={connected} event={event} />

      <main className="main-content">
        <Routes>
          <Route path="/" element={<AttendeeView />} />
          <Route path="/admin" element={<AdminDashboard />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppShell />
    </BrowserRouter>
  );
}
