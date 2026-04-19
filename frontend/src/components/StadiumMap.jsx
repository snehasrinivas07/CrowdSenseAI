/**
 * StadiumMap — SVG top-down stadium heatmap
 * 14 zones at hardcoded positions, color-coded by density.
 * Smooth CSS transitions, hover tooltip with zone name/density/wait/trend.
 */

import { useState } from "react";

// ─── colour helpers ────────────────────────────────────────────────────────

function densityColor(density) {
  if (density < 40) return "#1D9E75";   // green
  if (density <= 70) return "#EF9F27";  // amber
  return "#E24B4A";                     // red
}

function densityOpacity(density) {
  return 0.15 + (density / 100) * 0.65;
}

function trendArrow(trend) {
  if (trend === "rising")  return "▲";
  if (trend === "falling") return "▼";
  return "●";
}

// ─── Zone layout (hardcoded positions per spec) ────────────────────────────

const ZONE_LAYOUT = [
  { id: "gate_a", x: 160, y: 10,  w: 80, h: 36 },
  { id: "gate_b", x: 440, y: 10,  w: 80, h: 36 },
  { id: "gate_c", x: 10,  y: 200, w: 36, h: 80 },
  { id: "gate_d", x: 634, y: 200, w: 36, h: 80 },
  { id: "conc_1", x: 100, y: 100, w: 90, h: 40 },
  { id: "conc_2", x: 490, y: 100, w: 90, h: 40 },
  { id: "conc_3", x: 100, y: 340, w: 90, h: 40 },
  { id: "conc_4", x: 490, y: 340, w: 90, h: 40 },
  { id: "rest_n", x: 270, y: 20,  w: 80, h: 36 },
  { id: "rest_s", x: 270, y: 424, w: 80, h: 36 },
  { id: "rest_e", x: 600, y: 180, w: 36, h: 80 },
  { id: "rest_w", x: 44,  y: 180, w: 36, h: 80 },
  { id: "exit_1", x: 220, y: 200, w: 60, h: 80 },
  { id: "exit_2", x: 400, y: 200, w: 60, h: 80 },
];

// ─── Tooltip ──────────────────────────────────────────────────────────────

function Tooltip({ zone, x, y, visible }) {
  if (!visible || !zone) return null;
  const color = densityColor(zone.density);
  return (
    <foreignObject x={x} y={y} width={180} height={110} style={{ overflow: "visible" }}>
      <div
        xmlns="http://www.w3.org/1999/xhtml"
        style={{
          background: "rgba(15,15,30,0.95)",
          border: `1px solid ${color}`,
          borderRadius: 10,
          padding: "10px 14px",
          color: "#f0f0f0",
          fontSize: 12,
          lineHeight: 1.6,
          boxShadow: `0 4px 20px ${color}44`,
          pointerEvents: "none",
          whiteSpace: "nowrap",
        }}
      >
        <div style={{ fontWeight: 700, fontSize: 13, color }}>{zone.name}</div>
        <div>Density: <b>{Math.round(zone.density)}%</b></div>
        <div>Wait: <b>{zone.wait_minutes} min</b></div>
        <div>
          Trend:{" "}
          <b style={{ color }}>
            {trendArrow(zone.trend)} {zone.trend}
          </b>
        </div>
        {zone.predicted_spike_in_minutes !== undefined && (
          <div style={{ color: "#EF9F27" }}>
            ⚡ Spike in ~{zone.predicted_spike_in_minutes} min
          </div>
        )}
      </div>
    </foreignObject>
  );
}

// ─── Main component ────────────────────────────────────────────────────────

export default function StadiumMap({ zones = [], highlightedZones = [] }) {
  const [tooltip, setTooltip] = useState({ zoneId: null, x: 0, y: 0 });

  // Build a lookup map for fast access
  const zoneData = {};
  zones.forEach((z) => { zoneData[z.id] = z; });

  const hoveredZone = zoneData[tooltip.zoneId] || null;

  return (
    <div className="stadium-map-wrapper">
      <svg
        viewBox="0 0 680 480"
        xmlns="http://www.w3.org/2000/svg"
        style={{ width: "100%", height: "100%", display: "block" }}
        role="img"
        aria-label="Live stadium crowd density map showing real-time crowd pressure across 14 zones"
      >
        <title>CrowdSense AI Stadium Heatmap</title>
        <desc>An interactive real-time heatmap showing crowd density levels across 14 stadium zones including gates, concessions, restrooms and exits. Colors range from green for low density to red for high density.</desc>

        {/* ── Stadium outline ── */}
        <rect
          x={8} y={8} width={664} height={464}
          rx={32} ry={32}
          fill="none"
          stroke="#334155"
          strokeWidth={2}
        />

        {/* ── Pitch / field in the centre ── */}
        <ellipse
          cx={340} cy={240}
          rx={120} ry={90}
          fill="#1a3a2a"
          stroke="#2d6a4f"
          strokeWidth={1.5}
        />
        <text
          x={340} y={244}
          textAnchor="middle"
          fill="#2d6a4f"
          fontSize={13}
          fontFamily="Inter, sans-serif"
          fontWeight={600}
          letterSpacing={2}
        >
          PITCH
        </text>

        {/* ── Zones ── */}
        {ZONE_LAYOUT.map((layout) => {
          const zone   = zoneData[layout.id];
          const density = zone ? zone.density : 0;
          const color   = densityColor(density);
          const opacity = densityOpacity(density);
          const isHighlighted = highlightedZones.includes(layout.id);
          const isHovered     = tooltip.zoneId === layout.id;

          const cx = layout.x + layout.w / 2;
          const cy = layout.y + layout.h / 2;

          // Label abbreviation
          const label = zone
            ? zone.name.replace("Restroom", "R.").replace("Concession", "C.").replace("Gate", "G.")
            : layout.id;

          return (
            <g
              key={layout.id}
              style={{ cursor: "pointer" }}
              onMouseEnter={(e) => {
                setTooltip({ zoneId: layout.id, x: layout.x, y: layout.y + layout.h + 6 });
              }}
              onMouseLeave={() => setTooltip({ zoneId: null, x: 0, y: 0 })}
            >
              {/* Glow ring for highlighted or hovered zones */}
              {(isHighlighted || isHovered) && (
                <rect
                  x={layout.x - 4}
                  y={layout.y - 4}
                  width={layout.w + 8}
                  height={layout.h + 8}
                  rx={8}
                  ry={8}
                  fill="none"
                  stroke={isHighlighted ? "#a78bfa" : color}
                  strokeWidth={2.5}
                  opacity={0.9}
                  style={{ filter: `drop-shadow(0 0 6px ${isHighlighted ? "#a78bfa" : color})` }}
                />
              )}

              {/* Zone fill */}
              <rect
                x={layout.x}
                y={layout.y}
                width={layout.w}
                height={layout.h}
                rx={6}
                ry={6}
                fill={color}
                fillOpacity={opacity}
                stroke={color}
                strokeOpacity={0.6}
                strokeWidth={1}
                role="img"
                tabIndex={0}
                aria-label={`${zone?.name || layout.id}: ${Math.round(density)}% capacity, ${zone?.wait_minutes || 0} minute wait, crowd is ${zone?.trend || "stable"}`}
                onKeyPress={(e) => {
                  if (e.key === "Enter") {
                    setTooltip({ zoneId: layout.id, x: layout.x, y: layout.y + layout.h + 6 });
                  }
                }}
                style={{ transition: "fill 0.6s ease, fill-opacity 0.6s ease" }}
              />

              {/* Zone label */}
              <text
                x={cx}
                y={cy + 1}
                textAnchor="middle"
                dominantBaseline="middle"
                fill="#ffffff"
                fontSize={layout.w < 45 ? 7 : 9}
                fontFamily="Inter, sans-serif"
                fontWeight={600}
                style={{ pointerEvents: "none", userSelect: "none" }}
              >
                {label}
              </text>

              {/* Density badge */}
              {zone && (
                <text
                  x={cx}
                  y={cy + (layout.h > 50 ? 12 : 11)}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill="#ffffffcc"
                  fontSize={7}
                  fontFamily="Inter, sans-serif"
                  style={{ pointerEvents: "none", userSelect: "none" }}
                >
                  {Math.round(density)}%
                </text>
              )}
            </g>
          );
        })}

        {/* ── Tooltip ── */}
        {tooltip.zoneId && (
          <Tooltip
            zone={hoveredZone}
            x={Math.min(tooltip.x, 490)}
            y={tooltip.y}
            visible
          />
        )}
      </svg>
    </div>
  );
}
