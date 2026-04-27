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
  const [interruption, setInterruption] = useState<
    { last_seq: number; last_event?: string } | null
  >(null);
  // Live "thinking" buffer per agent — accumulated from `chunk` events
  // so the UI can show streaming progress while a worker is producing
  // its 30-60s response. Cleared on each new submit.
  const [workerThoughts, setWorkerThoughts] = useState<Record<string, string>>(
    {},
  );
  const abortRef = useRef<AbortController | null>(null);

  async function handleSubmit(req: ResearchRequest) {
    setBusy(true);
    setEvents([]);
    setBriefing(null);
    setError(null);
    setToolWarnings([]);
    setInterruption(null);
    setWorkerThoughts({});

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await runResearch(req, {
        signal: controller.signal,
        onEvent: (evt) => {
          // Token-stream chunks would drown the event log; route them
          // into a separate per-agent live buffer instead. The
          // StreamingViewer renders a "thinking" panel for any agent
          // that has thoughts but hasn't emitted ``partial`` yet.
          if (evt.type === "chunk") {
            setWorkerThoughts((prev) => ({
              ...prev,
              [evt.agent]: (prev[evt.agent] ?? "") + evt.delta,
            }));
            return;
          }
          // ``stream_interrupted`` is synthesised by the client when
          // the response body EOFs without a terminal ``done`` event.
          // That means an intermediary (Vite dev proxy, ACA ingress,
          // browser fetch, etc.) cut the connection mid-flight. Show
          // an explicit banner so the user sees "this failed" instead
          // of "this finished with partial results".
          if (evt.type === "stream_interrupted") {
            setInterruption({
              last_seq: evt.last_seq,
              last_event: evt.last_event,
            });
            return;
          }
          // ``done`` is the terminal protocol marker. Nothing to render
          // — its absence is what matters (handled above).
          if (evt.type === "done") return;

          setEvents((prev) => [...prev, evt]);
          // ``briefing_ready`` makes the briefing renderable BEFORE
          // any side-effect tools fire, so a HITL/permission failure
          // afterwards no longer wipes the four agents' output.
          // ``final`` carries the same briefing — handle both.
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

  // Partials that arrived before the stream died — exposed so the
  // interruption banner can tell the user how far we got.
  const partials = events
    .filter((e): e is Extract<StreamEvent, { type: "partial" }> => e.type === "partial")
    .map((e) => ({ worker_id: e.worker_id, output: e.output }));

  // An agent is "still thinking" if we've seen chunks but no partial yet.
  const completedWorkers = new Set(partials.map((p) => p.worker_id));
  const liveThoughts = Object.entries(workerThoughts).filter(
    ([agent]) => !completedWorkers.has(agent),
  );

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
        {interruption && !briefing && (
          <div className="card error" role="alert">
            <strong>Stream disconnected before the briefing was ready.</strong>
            <p className="muted">
              The connection was cut by an intermediary after{" "}
              <code>seq={interruption.last_seq}</code>
              {interruption.last_event && (
                <>
                  {" "}
                  (last event: <code>{interruption.last_event}</code>)
                </>
              )}
              . {partials.length > 0
                ? `${partials.length} of 4 worker output(s) arrived before the cut — see them under "Streaming activity" below.`
                : "No worker output arrived before the cut."}
              {" "}This is a transport issue, not a model failure — try again,
              or check the dev proxy / ingress timeouts.
            </p>
          </div>
        )}
        {interruption && briefing && (
          <div className="card warn" role="status">
            <strong>Stream disconnected after the briefing was ready.</strong>
            <p className="muted">
              The briefing below is complete, but the connection was cut at{" "}
              <code>seq={interruption.last_seq}</code> before we could confirm
              completion. Side-effect tool results may be missing.
            </p>
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
        <StreamingViewer
          events={events}
          busy={busy}
          liveThoughts={liveThoughts}
        />
        <ResultPanel briefing={briefing} />
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
