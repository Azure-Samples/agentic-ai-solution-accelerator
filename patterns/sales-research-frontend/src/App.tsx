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
  const abortRef = useRef<AbortController | null>(null);

  async function handleSubmit(req: ResearchRequest) {
    setBusy(true);
    setEvents([]);
    setBriefing(null);
    setError(null);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await runResearch(req, {
        signal: controller.signal,
        onEvent: (evt) => {
          setEvents((prev) => [...prev, evt]);
          if (evt.type === "final") setBriefing(evt.briefing);
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
        <StreamingViewer events={events} busy={busy} />
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
