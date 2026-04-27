import { useMemo, useRef, useState } from "react";
import { ResearchForm } from "./components/ResearchForm";
import { StreamingViewer } from "./components/StreamingViewer";
import { ResultPanel } from "./components/ResultPanel";
import { HeroCard } from "./components/HeroCard";
import { SectionNav, type NavSection, type SectionStatus } from "./components/SectionNav";
import { PendingApproval } from "./components/PendingApproval";
import { runResearch, RESEARCH_STREAM_URL } from "./services/researchClient";
import type { ResearchBriefing, ResearchRequest, StreamEvent } from "./types/research";

interface ToolPendingApproval {
  tool: string;
  args: Record<string, unknown>;
}

const NAV_BLUEPRINT: { id: string; label: string; key: SectionKey }[] = [
  { id: "section-summary", label: "Summary", key: "supervisor" },
  { id: "section-account_planner", label: "Account profile", key: "account_planner" },
  { id: "section-icp_fit_analyst", label: "ICP fit", key: "icp_fit_analyst" },
  { id: "section-competitive_context", label: "Competitive", key: "competitive_context" },
  { id: "section-outreach_personalizer", label: "Outreach", key: "outreach_personalizer" },
  { id: "section-next_steps", label: "Next steps", key: "supervisor" },
  { id: "section-approvals", label: "Approvals", key: "approvals" },
];

type SectionKey =
  | "supervisor"
  | "account_planner"
  | "icp_fit_analyst"
  | "competitive_context"
  | "outreach_personalizer"
  | "approvals";

export default function App() {
  const [busy, setBusy] = useState(false);
  const [submittedRequest, setSubmittedRequest] = useState<ResearchRequest | null>(null);
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [briefing, setBriefing] = useState<ResearchBriefing | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toolWarnings, setToolWarnings] = useState<
    { tool: string; error: string }[]
  >([]);
  const [pendingApprovals, setPendingApprovals] = useState<ToolPendingApproval[]>([]);
  const [interruption, setInterruption] = useState<
    { last_seq: number; last_event?: string } | null
  >(null);
  // Live "thinking" indicator per worker. We keep a CHAR COUNT only —
  // not the raw text — because the UI only needs "this worker has
  // produced N chars so far" to drive the rotating progress copy.
  // Storing raw text caused multi-MB renders during long runs.
  const [workerProgress, setWorkerProgress] = useState<Record<string, number>>({});
  // Workers that have completed (success OR skipped). Used to clear
  // "is working" indicators. Kept separate from the events list so we
  // can mark the supervisor done on briefing_ready without injecting
  // a synthetic event.
  const [completedWorkers, setCompletedWorkers] = useState<Set<string>>(new Set());
  const [formCollapsed, setFormCollapsed] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  async function handleSubmit(req: ResearchRequest) {
    setBusy(true);
    setSubmittedRequest(req);
    setEvents([]);
    setBriefing(null);
    setError(null);
    setToolWarnings([]);
    setPendingApprovals([]);
    setInterruption(null);
    setWorkerProgress({});
    setCompletedWorkers(new Set());
    setFormCollapsed(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await runResearch(req, {
        signal: controller.signal,
        onEvent: (evt) => {
          if (evt.type === "chunk") {
            // Backend tags chunks with worker_id (matches partial.worker_id).
            // ``agent`` (Foundry agent name) is kept as a fallback for
            // older deployments and for the supervisor (no worker_id).
            const key = evt.worker_id ?? evt.agent;
            const len = evt.delta.length;
            setWorkerProgress((prev) => ({
              ...prev,
              [key]: (prev[key] ?? 0) + len,
            }));
            return;
          }
          if (evt.type === "worker_started") {
            // Seed the progress map so a SectionLoader card appears
            // immediately, well before the first token arrives. Cold
            // replicas can take 5-15s to produce the first chunk.
            setWorkerProgress((prev) => ({
              ...prev,
              [evt.worker_id]: prev[evt.worker_id] ?? 0,
            }));
            setEvents((prev) => [...prev, evt]);
            return;
          }
          if (evt.type === "stream_interrupted") {
            setInterruption({
              last_seq: evt.last_seq,
              last_event: evt.last_event,
            });
            return;
          }
          if (evt.type === "done") return;

          setEvents((prev) => [...prev, evt]);

          if (evt.type === "partial") {
            setCompletedWorkers((prev) => {
              const next = new Set(prev);
              next.add(evt.worker_id);
              return next;
            });
          }
          if (evt.type === "worker_skipped") {
            setCompletedWorkers((prev) => {
              const next = new Set(prev);
              next.add(evt.worker_id);
              return next;
            });
          }
          if (evt.type === "briefing_ready" || evt.type === "final") {
            setBriefing(evt.briefing);
            // Supervisor never emits ``partial`` — it streams chunks
            // straight into the briefing. Mark it complete here so
            // the live-thoughts card stops pulsing.
            setCompletedWorkers((prev) => {
              const next = new Set(prev);
              next.add("supervisor");
              return next;
            });
          }
          if (evt.type === "tool_pending_approval") {
            setPendingApprovals((prev) => [
              ...prev,
              { tool: evt.tool, args: evt.args },
            ]);
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

  function handleEditRequest() {
    setFormCollapsed(false);
  }

  const partials = events
    .filter((e): e is Extract<StreamEvent, { type: "partial" }> => e.type === "partial")
    .map((e) => ({ worker_id: e.worker_id, output: e.output }));

  // Live thoughts: workers we've seen progress for that haven't completed.
  // Pass char counts so the StreamingViewer can drive its rotating copy.
  const liveThoughts: [string, number][] = useMemo(() => {
    return Object.entries(workerProgress).filter(
      ([key]) => !completedWorkers.has(key),
    );
  }, [workerProgress, completedWorkers]);

  // Section nav status — drives the chip pulses.
  const navSections: NavSection[] = useMemo(() => {
    function statusFor(key: SectionKey): SectionStatus {
      if (key === "approvals") {
        return pendingApprovals.length > 0 ? "ready" : "waiting";
      }
      if (key === "supervisor") {
        if (briefing) return "ready";
        if (workerProgress["supervisor"] !== undefined) return "live";
        return "waiting";
      }
      // worker keys
      if (completedWorkers.has(key)) {
        // could be skipped — check events
        const skipped = events.some(
          (e) => e.type === "worker_skipped" && e.worker_id === key,
        );
        if (skipped) return "skipped";
        return "ready";
      }
      if (workerProgress[key] !== undefined) return "live";
      return "waiting";
    }
    return NAV_BLUEPRINT
      .filter((b) => b.key !== "approvals" || pendingApprovals.length > 0)
      .map((b) => ({
        id: b.id,
        label: b.label,
        status: statusFor(b.key),
      }));
  }, [briefing, workerProgress, completedWorkers, events, pendingApprovals]);

  const hasOutput = submittedRequest !== null;

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header-inner">
          <div>
            <h1>Sales Research</h1>
            <p className="muted">
              Multi-agent research briefing &mdash; partner-grade reference UI for{" "}
              <code>{RESEARCH_STREAM_URL}</code>
            </p>
          </div>
          {hasOutput && busy && (
            <span className="header-status">
              <span className="pulse" aria-hidden="true" />
              Researching...
            </span>
          )}
        </div>
      </header>

      <main className={hasOutput ? "main-with-output" : "main-empty"}>
        <aside
          className={`form-pane ${formCollapsed ? "form-pane-collapsed" : ""}`}
          aria-label="Research configuration"
        >
          {formCollapsed && submittedRequest ? (
            <div className="form-summary">
              <div className="form-summary-text">
                <strong>{submittedRequest.company_name}</strong>
                <span className="muted">
                  &nbsp;&middot;&nbsp;{submittedRequest.persona || "no persona"}
                </span>
              </div>
              <button
                type="button"
                className="link-btn"
                onClick={handleEditRequest}
                disabled={busy}
              >
                Edit request
              </button>
            </div>
          ) : (
            <ResearchForm
              busy={busy}
              onSubmit={handleSubmit}
              onCancel={handleCancel}
            />
          )}
        </aside>

        <section className="output-pane" aria-label="Briefing output">
          {!hasOutput && (
            <div className="empty-state">
              <h2>Ready when you are</h2>
              <p className="muted">
                Configure the request on the left (or load a sector archetype) and
                click <strong>Run research</strong> to stream a multi-agent briefing.
              </p>
            </div>
          )}

          {hasOutput && (
            <>
              <HeroCard
                request={submittedRequest}
                briefing={briefing}
                events={events}
                busy={busy}
              />

              <SectionNav sections={navSections} />

              {error && (
                <div className="card error" role="alert">
                  <strong>Error:</strong> {error}
                </div>
              )}
              {interruption && !briefing && (
                <div className="card error" role="alert">
                  <strong>Stream disconnected before the briefing was ready.</strong>
                  <p className="muted">
                    The connection was cut after{" "}
                    <code>seq={interruption.last_seq}</code>
                    {interruption.last_event && (
                      <>
                        {" "}
                        (last event: <code>{interruption.last_event}</code>)
                      </>
                    )}
                    .{" "}
                    {partials.length > 0
                      ? `${partials.length} of 4 worker output(s) arrived before the cut.`
                      : "No worker output arrived before the cut."}
                    {" "}
                    Try again or check the dev proxy / ingress timeouts.
                  </p>
                </div>
              )}
              {interruption && briefing && (
                <div className="card warn" role="status">
                  <strong>Stream disconnected after the briefing was ready.</strong>
                  <p className="muted">
                    The briefing below is complete, but the connection was cut at{" "}
                    <code>seq={interruption.last_seq}</code>.
                  </p>
                </div>
              )}
              {toolWarnings.length > 0 && (
                <div className="card warn" role="status">
                  <strong>Side-effect tools failed during execution.</strong>
                  <ul>
                    {toolWarnings.map((w, i) => (
                      <li key={i}>
                        <code>{w.tool}</code>: {w.error}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <ResultPanel briefing={briefing} events={events} />

              <PendingApproval approvals={pendingApprovals} />

              <details className="activity-details">
                <summary>Streaming activity ({events.length} events)</summary>
                <StreamingViewer
                  events={events}
                  busy={busy}
                  liveThoughts={liveThoughts}
                />
              </details>
            </>
          )}
        </section>
      </main>

      <footer className="app-footer">
        <span>
          Pattern source: <code>patterns/sales-research-frontend/</code> &middot;
          fork to customise per customer.
        </span>
      </footer>
    </div>
  );
}
