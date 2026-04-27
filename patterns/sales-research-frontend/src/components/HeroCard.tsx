import type { ResearchBriefing, ResearchRequest, StreamEvent } from "../types/research";

interface Props {
  request: ResearchRequest | null;
  briefing: ResearchBriefing | null;
  events: StreamEvent[];
  busy: boolean;
}

// Pulls a numeric ICP fit score out of the icp_fit_analyst partial or
// the supervisor's icp_fit field. The schema doesn't pin a single key
// name (different prompts emit ``fit_score``, ``score``, etc.) so we
// scan a few common variants. Returns null when nothing usable is
// present, and the chip is hidden.
function extractScore(briefing: ResearchBriefing | null, events: StreamEvent[]): number | null {
  const candidates: unknown[] = [];
  if (briefing?.icp_fit) candidates.push(briefing.icp_fit);
  for (const e of events) {
    if (e.type === "partial" && e.worker_id === "icp_fit_analyst") {
      candidates.push(e.output);
    }
  }
  for (const c of candidates) {
    if (c && typeof c === "object" && !Array.isArray(c)) {
      const obj = c as Record<string, unknown>;
      for (const k of ["fit_score", "score", "icp_fit_score", "fit"]) {
        const v = obj[k];
        if (typeof v === "number") return v;
        if (typeof v === "string") {
          const n = Number(v);
          if (!Number.isNaN(n)) return n;
        }
      }
    }
  }
  return null;
}

function countSignals(briefing: ResearchBriefing | null, events: StreamEvent[]): number {
  const sources: unknown[] = [];
  if (briefing?.account_profile) sources.push(briefing.account_profile);
  for (const e of events) {
    if (e.type === "partial" && e.worker_id === "account_planner") {
      sources.push(e.output);
    }
  }
  for (const src of sources) {
    if (src && typeof src === "object" && !Array.isArray(src)) {
      const obj = src as Record<string, unknown>;
      const ev = obj["signal_evidence"] ?? obj["signals"] ?? obj["recent_news"];
      if (Array.isArray(ev)) return ev.length;
    }
  }
  return 0;
}

export function HeroCard({ request, briefing, events, busy }: Props) {
  if (!request) return null;
  const score = extractScore(briefing, events);
  const signalCount = countSignals(briefing, events);
  const status = briefing
    ? "ready"
    : busy
      ? "researching"
      : "idle";
  return (
    <section className="hero-card" aria-label="Research subject">
      <div className="hero-main">
        <div className="hero-eyebrow">
          <span className={`hero-status hero-status-${status}`}>
            {status === "ready" && "● Briefing ready"}
            {status === "researching" && "● Researching"}
            {status === "idle" && "● Awaiting input"}
          </span>
          {request.domain && (
            <span className="hero-domain">
              <code>{request.domain}</code>
            </span>
          )}
        </div>
        <h2 className="hero-title">{request.company_name}</h2>
        <p className="hero-intent">{request.seller_intent}</p>
      </div>
      <div className="hero-stats" role="group" aria-label="Briefing stats">
        {score !== null && (
          <div className="hero-stat">
            <span className="hero-stat-label">ICP fit</span>
            <span className={`hero-stat-value hero-score-${scoreTone(score)}`}>
              {formatScore(score)}
            </span>
          </div>
        )}
        <div className="hero-stat">
          <span className="hero-stat-label">Signals</span>
          <span className="hero-stat-value">{signalCount || "—"}</span>
        </div>
        <div className="hero-stat">
          <span className="hero-stat-label">Persona</span>
          <span className="hero-stat-value hero-stat-text">{request.persona || "—"}</span>
        </div>
      </div>
    </section>
  );
}

function formatScore(n: number): string {
  if (n <= 1) return `${Math.round(n * 100)}`;
  return `${Math.round(n)}`;
}

function scoreTone(n: number): "high" | "med" | "low" {
  const pct = n <= 1 ? n * 100 : n;
  if (pct >= 70) return "high";
  if (pct >= 40) return "med";
  return "low";
}
