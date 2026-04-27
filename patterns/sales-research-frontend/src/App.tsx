import { useRef, useState } from "react";
import { ResearchForm } from "./components/ResearchForm";
import { StreamingViewer } from "./components/StreamingViewer";
import { ResultPanel } from "./components/ResultPanel";
import { runResearch, RESEARCH_STREAM_URL } from "./services/researchClient";
import type { ResearchBriefing, ResearchRequest, StreamEvent } from "./types/research";

export default function App() {
  const [busy, setBusy] = useState(false);
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [briefing, setBriefing] = useState<ResearchBriefing | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toolWarnings, setToolWarnings] = useState<
    { tool: string; error: string }[]
  >([]);
  const abortRef = useRef<AbortController | null>(null);

  async function handleSubmit(req: ResearchRequest) {
    setBusy(true);
    setEvents([]);
    setBriefing(null);
    setError(null);
    setToolWarnings([]);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await runResearch(req, {
        signal: controller.signal,
        onEvent: (evt) => {
          setEvents((prev) => [...prev, evt]);
          // ``briefing_ready`` makes the briefing renderable BEFORE
          // any side-effect tools fire, so a HITL/permission failure
          // afterwards no longer wipes the four agents' output.
          // ``final`` is the terminal event and carries the same
          // briefing — handle both so older backends still render.
          if (evt.type === "briefing_ready" || evt.type === "final") {
            setBriefing(evt.briefing);
          }
          if (evt.type === "tool_error") {
            setToolWarnings((prev) => [
              ...prev,
              { tool: evt.tool, error: evt.error },
            ]);
          }
          if (evt.type === "error") setError(evt.message);
        },
      });
    } catch (err) {
      if ((err as Error).name === "AbortError") {
        setError("Cancelled.");
      } else {
        setError((err as Error).message);
      }
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  }

  function handleCancel() {
    abortRef.current?.abort();
  }

  // Defensive fallback: if the backend never emits ``briefing_ready``
  // or ``final`` (e.g. fatal error during aggregation), surface the
  // raw worker outputs so the four agents' work isn't lost from view.
  // We don't fabricate a ResearchBriefing — we just expose the
  // partials directly, clearly labelled as partial results.
  const partials = events
    .filter((e): e is Extract<StreamEvent, { type: "partial" }> => e.type === "partial")
    .map((e) => ({ worker_id: e.worker_id, output: e.output }));
  const showPartialFallback = !briefing && partials.length > 0;

  return (
    <div className="app">
      <header className="app-header">
        <h1>Sales Research — reference UI</h1>
        <p className="muted">
          Streaming client for <code>{RESEARCH_STREAM_URL}</code>. Reference
          starter — fork and customise for your customer.
        </p>
      </header>

      <main>
        <ResearchForm busy={busy} onSubmit={handleSubmit} onCancel={handleCancel} />
        {error && (
          <div className="card error" role="alert">
            <strong>Error:</strong> {error}
          </div>
        )}
        {toolWarnings.length > 0 && (
          <div className="card warn" role="status">
            <strong>Side-effect tools needed approval — briefing is below.</strong>
            <ul>
              {toolWarnings.map((w, i) => (
                <li key={i}>
                  <code>{w.tool}</code>: {w.error}
                </li>
              ))}
            </ul>
          </div>
        )}
        <StreamingViewer events={events} busy={busy} />
        <ResultPanel briefing={briefing} />
        {showPartialFallback && (
          <div className="card">
            <h2>Partial results (no final briefing)</h2>
            <p className="muted">
              The backend did not emit a final briefing. The raw outputs
              from each worker that did complete are shown below.
            </p>
            {partials.map((p) => (
              <details key={p.worker_id} className="partial-block">
                <summary>{p.worker_id}</summary>
                <pre className="raw-json">{JSON.stringify(p.output, null, 2)}</pre>
              </details>
            ))}
          </div>
        )}
      </main>

      <footer className="app-footer">
        <span>
          Pattern source:{" "}
          <code>patterns/sales-research-frontend/</code>
        </span>
      </footer>
    </div>
  );
}
