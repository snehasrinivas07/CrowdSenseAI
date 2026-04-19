/**
 * useCrowdStream — React hook
 * Connects to WS /ws/crowd, auto-reconnects on disconnect every 3 s.
 * Exposes: { zones, event, summary, connected, triggerEvent }
 */

import { useCallback, useEffect, useRef, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

/** Derive WebSocket URL from the REST base URL (https→wss, http→ws) */
function deriveWsUrl(apiUrl) {
  return apiUrl.replace(/^https/, "wss").replace(/^http/, "ws") + "/ws/crowd";
}

export function useCrowdStream() {
  const [zones, setZones] = useState([]);
  const [event, setEvent] = useState("IN_PLAY");
  const [summary, setSummary] = useState(null);
  const [connected, setConnected] = useState(false);

  const wsRef = useRef(null);
  const reconnectTimer = useRef(null);
  const mountedRef = useRef(true);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;

    const url = deriveWsUrl(API_URL);
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      if (mountedRef.current) setConnected(true);
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current);
        reconnectTimer.current = null;
      }
    };

    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (mountedRef.current) {
          setZones(data.zones || []);
          setEvent(data.event || "IN_PLAY");
          setSummary(data.summary || null);
        }
      } catch (err) {
        console.error("[useCrowdStream] parse error", err);
      }
    };

    ws.onerror = () => {
      ws.close();
    };

    ws.onclose = () => {
      if (mountedRef.current) {
        setConnected(false);
        // Auto-reconnect after 3 seconds
        reconnectTimer.current = setTimeout(() => {
          if (mountedRef.current) connect();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connect]);

  // Vercel/Serverless Fallback: Poll if WebSocket is not connected
  useEffect(() => {
    let pollTimer = null;
    if (!connected && mountedRef.current) {
      pollTimer = setInterval(async () => {
        try {
          const res = await fetch(`${API_URL}/crowd/state`);
          if (!res.ok) return;
          const data = await res.json();
          if (mountedRef.current) {
            setZones(data.zones || []);
            setEvent(data.event || "IN_PLAY");
            setSummary(data.summary || null);
          }
        } catch (err) {
          // Log quiet fallback error
        }
      }, 5000); // 5-second polling
    }
    return () => {
      if (pollTimer) clearInterval(pollTimer);
    };
  }, [connected]);

  /** Trigger a stadium event via REST, then the WS broadcast catches up. */
  const triggerEvent = useCallback(async (eventName) => {
    try {
      await fetch(`${API_URL}/events/trigger`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ event: eventName }),
      });
    } catch (err) {
      console.error("[useCrowdStream] triggerEvent error", err);
    }
  }, []);

  return { zones, event, summary, connected, triggerEvent };
}
