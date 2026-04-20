/**
 * CrowdChat — compact chat widget grounded in live crowd data.
 * Sends POST /chat with message + history.
 * Highlights referenced zone IDs on the stadium map via onZoneHighlight callback.
 * Includes 5 seeded demo queries.
 */

import { useCallback, useEffect, useRef, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const DEMO_QUERIES = [
  "Where's the shortest food queue?",
  "Which restroom has the least wait time?",
  "Which gate should I use to exit fastest?",
  "Is Concession 1 busy right now?",
  "Where should I go during half-time?",
];

// Zone IDs the backend might reference — used to highlight on map
const ZONE_ID_MAP = {
  "gate a":       "gate_a",
  "gate b":       "gate_b",
  "gate c":       "gate_c",
  "gate d":       "gate_d",
  "concession 1": "conc_1",
  "concession 2": "conc_2",
  "concession 3": "conc_3",
  "concession 4": "conc_4",
  "restroom north": "rest_n",
  "restroom south": "rest_s",
  "restroom east":  "rest_e",
  "restroom west":  "rest_w",
  "exit 1":       "exit_1",
  "exit 2":       "exit_2",
};

function extractZoneIds(text) {
  const lower = text.toLowerCase();
  return Object.entries(ZONE_ID_MAP)
    .filter(([name]) => lower.includes(name))
    .map(([, id]) => id);
}

function ChatBubble({ msg }) {
  const isUser = msg.role === "user";
  return (
    <div className={`chat-bubble-row ${isUser ? "user" : "assistant"}`}>
      {!isUser && (
        <div className="chat-avatar">🤖</div>
      )}
      <div className={`chat-bubble ${isUser ? "user" : "assistant"}`}>
        <p>{msg.content}</p>
      </div>
      {isUser && (
        <div className="chat-avatar user-avatar">👤</div>
      )}
    </div>
  );
}

export default function CrowdChat({ onZoneHighlight }) {
  const [history, setHistory]   = useState([]);
  const [input, setInput]       = useState("");
  const [loading, setLoading]   = useState(false);
  const bottomRef               = useRef(null);
  const inputRef                = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history]);

  const sendMessage = useCallback(async (text) => {
    const msg = text.trim();
    if (!msg || loading) return;

    const newHistory = [...history, { role: "user", content: msg }];
    setHistory(newHistory);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ message: msg, history }),
      });
      const data = await res.json();
      const answer = data.reply || data.answer || "Sorry, I couldn't get an answer right now.";

      const updatedHistory = [...newHistory, { role: "assistant", content: answer }];
      setHistory(updatedHistory);

      // Highlight zones mentioned in the answer
      const zones = extractZoneIds(answer);
      if (zones.length > 0 && onZoneHighlight) {
        onZoneHighlight(zones);
        // Clear highlights after 4 s
        setTimeout(() => onZoneHighlight([]), 4000);
      }
    } catch (err) {
      console.error("[CrowdChat] error", err);
      setHistory((h) => [
        ...h,
        { role: "assistant", content: "Connection error — please try again." },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  }, [history, loading, onZoneHighlight]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  return (
    <div className="crowd-chat">
      <div className="chat-header">
        <span className="chat-header-icon">💬</span>
        <h2 className="chat-title">Ask CrowdSense</h2>
        <span className="chat-live-badge">LIVE</span>
      </div>

      {/* Demo seed queries */}
      {history.length === 0 && (
        <div className="chat-seeds">
          {DEMO_QUERIES.map((q) => (
            <button
              key={q}
              className="chat-seed-btn"
              onClick={() => sendMessage(q)}
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Message history */}
      <div className="chat-messages" role="log" aria-live="polite" aria-label="Chat responses">
        {history.map((msg, i) => (
          <ChatBubble key={i} msg={msg} />
        ))}
        {loading && (
          <div className="chat-bubble-row assistant">
            <div className="chat-avatar">🤖</div>
            <div className="chat-bubble assistant typing">
              <span className="dot" /><span className="dot" /><span className="dot" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="chat-input-row">
        <input
          ref={inputRef}
          className="chat-input"
          type="text"
          placeholder="Ask about any zone…"
          aria-label="Ask a question about current crowd conditions"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
        />
        <button
          className="chat-send-btn"
          onClick={() => sendMessage(input)}
          disabled={loading || !input.trim()}
        >
          ↗
        </button>
      </div>
    </div>
  );
}
