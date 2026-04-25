import type { StreamEvent } from "../types/research";

interface Props {
  events: StreamEvent[];
  busy: boolean;
}

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
    case "tool_skipped":
      return { label: `tool skipped · ${event.tool} (${event.reason})`, tone: "warn" };
    case "tool_result":
      return { label: `tool result · ${event.tool}`, tone: "ok" };
    case "final":
      return { label: "final briefing assembled", tone: "ok" };
    case "error":
      return { label: `error · ${event.message}`, tone: "err" };
  }
}

export function StreamingViewer({ events, busy }: Props) {
  if (events.length === 0 && !busy) return null;
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
    </div>
  );
}
