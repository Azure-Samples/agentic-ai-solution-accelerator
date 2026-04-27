import { useEffect, useRef } from "react";
import type { StreamEvent } from "../types/research";

interface Props {
  events: StreamEvent[];
  busy: boolean;
  // Per-agent live thinking buffer (chunks accumulated since the agent
  // started but before it emitted ``partial``). The viewer renders the
  // tail of each buffer so the user can see the model is working —
  // critical for 30-60s gpt-5-mini calls that would otherwise look hung.
  liveThoughts?: [agent: string, text: string][];
}

// How many trailing characters of streaming text to show. The full
// payload is JSON 5-15 kB and not useful to display — but the tail is
// useful as a "still alive" signal.
const THOUGHT_TAIL_CHARS = 600;

function describe(event: StreamEvent): { label: string; tone: string } {
  switch (event.type) {
    case "status":
      return { label: `status · ${event.stage}`, tone: "info" };
    case "partial":
      return { label: `worker complete · ${event.worker_id}`, tone: "ok" };
    case "worker_skipped":
      return {
        label: `worker skipped · ${event.worker_id}${event.error ? ` (${event.error})` : ""}`,
        tone: "warn",
      };
    case "briefing_ready":
      return { label: "briefing ready (rendering)", tone: "ok" };
    case "tool_skipped":
      return { label: `tool skipped · ${event.tool} (${event.reason})`, tone: "warn" };
    case "tool_result":
      return { label: `tool result · ${event.tool}`, tone: "ok" };
    case "tool_error":
      return { label: `tool error · ${event.tool} (${event.error})`, tone: "warn" };
    case "final":
      return { label: "final briefing assembled", tone: "ok" };
    case "error":
      return { label: `error · ${event.message}`, tone: "err" };
    // ``chunk`` and ``heartbeat`` are routed before reaching this list,
    // but TypeScript wants the union exhausted.
    case "chunk":
      return { label: `chunk · ${event.agent}`, tone: "info" };
    case "heartbeat":
      return { label: "heartbeat", tone: "info" };
  }
}

export function StreamingViewer({ events, busy, liveThoughts }: Props) {
  const thoughtsRef = useRef<HTMLDivElement | null>(null);
  // Auto-scroll the thoughts panel to the bottom as new chunks arrive.
  useEffect(() => {
    if (thoughtsRef.current) {
      thoughtsRef.current.scrollTop = thoughtsRef.current.scrollHeight;
    }
  }, [liveThoughts]);

  if (events.length === 0 && !busy && !liveThoughts?.length) return null;
  return (
    <div className="card">
      <h2>
        Live stream
        {busy && <span className="pulse" aria-label="streaming" />}
      </h2>
      <ol className="event-log">
        {events.map((evt, i) => {
          const { label, tone } = describe(evt);
          return (
            <li key={i} className={`event event-${tone}`}>
              <span className="event-index">{i + 1}</span>
              <span className="event-label">{label}</span>
            </li>
          );
        })}
      </ol>
      {liveThoughts && liveThoughts.length > 0 && (
        <div className="live-thoughts" ref={thoughtsRef}>
          {liveThoughts.map(([agent, text]) => (
            <div key={agent} className="live-thought">
              <span className="thought-agent">
                <span className="pulse" aria-hidden="true" /> {agent} is thinking…
              </span>
              <pre className="thought-text">
                {text.length > THOUGHT_TAIL_CHARS
                  ? "…" + text.slice(-THOUGHT_TAIL_CHARS)
                  : text}
              </pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
