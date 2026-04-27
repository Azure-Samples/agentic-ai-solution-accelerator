import { useCallback, useMemo, useState } from "react";
import type { ResearchBriefing, StreamEvent } from "../types/research";
import { SectionLoader } from "./SectionLoader";

interface Props {
  briefing: ResearchBriefing | null;
  events: StreamEvent[];
}

// ---------------------------------------------------------------------------
// Markdown serialiser — converts structured data to pasteable markdown.
// Handles the known shapes (string[], Record, nested arrays) so each
// section's copy button produces clean output for Teams / Outlook / CRM.
// ---------------------------------------------------------------------------

function valueToMarkdown(value: unknown, indent = 0): string {
  if (value === null || value === undefined || value === "") return "_not available_";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) {
    if (value.length === 0) return "_(none)_";
    if (value.every((x) => typeof x === "string")) {
      return value.map((s) => `- ${s}`).join("\n");
    }
    if (value.every((x) => typeof x === "object" && x !== null && !Array.isArray(x))) {
      return (value as Record<string, unknown>[])
        .map((row) => recordToMarkdown(row, indent))
        .join("\n\n");
    }
    return value.map((v) => `- ${String(v)}`).join("\n");
  }
  if (typeof value === "object") {
    return recordToMarkdown(value as Record<string, unknown>, indent);
  }
  return String(value);
}

function recordToMarkdown(data: Record<string, unknown>, indent = 0): string {
  const prefix = "  ".repeat(indent);
  return Object.entries(data)
    .map(([k, v]) => {
      const label = k.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
      if (typeof v === "object" && v !== null && !Array.isArray(v)) {
        return `${prefix}**${label}:**\n${valueToMarkdown(v, indent + 1)}`;
      }
      if (Array.isArray(v)) {
        return `${prefix}**${label}:**\n${valueToMarkdown(v, indent + 1)}`;
      }
      return `${prefix}**${label}:** ${valueToMarkdown(v)}`;
    })
    .join("\n");
}

function sectionToMarkdown(title: string, data: unknown): string {
  return `## ${title}\n\n${valueToMarkdown(data)}`;
}

// ---------------------------------------------------------------------------
// Copy button
// ---------------------------------------------------------------------------

function CopyButton({ title, data }: { title: string; data: unknown }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async () => {
    try {
      const md = sectionToMarkdown(title, data);
      await navigator.clipboard.writeText(md);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API may fail in insecure contexts — silent fallback.
    }
  }, [title, data]);

  return (
    <button
      type="button"
      className="copy-md-btn"
      onClick={handleCopy}
      title="Copy as markdown"
      aria-label={`Copy ${title} as markdown`}
    >
      {copied ? "✓ Copied" : "Copy"}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Section helpers
// ---------------------------------------------------------------------------

function Section({ id, title, data, children }: { id?: string; title: string; data?: unknown; children: React.ReactNode }) {
  return (
    <section id={id} className="result-section">
      <header className="section-header">
        <h3>{title}</h3>
        {data !== undefined && data !== null && <CopyButton title={title} data={data} />}
      </header>
      {children}
    </section>
  );
}

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function isStringArray(v: unknown): v is string[] {
  return Array.isArray(v) && v.every((x) => typeof x === "string");
}

// Pretty title for a snake_case key: "fit_score" -> "Fit score"
function humanise(key: string): string {
  const s = key.replace(/_/g, " ").trim();
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : key;
}

// ---------------------------------------------------------------------------
// Field-specific renderers
//
// Worker outputs ARE described by per-agent transform.py modules so we know
// the shapes. These renderers turn each shape into proper UI instead of
// JSON.stringify code blocks. Anything we don't recognise falls through to
// ``GenericValue`` which still avoids raw JSON for common shapes.
// ---------------------------------------------------------------------------

function NewsItem({ item }: { item: Record<string, unknown> }) {
  const title = String(item["title"] ?? "Untitled");
  const date = item["date"] ? String(item["date"]) : null;
  const summary = item["summary"] ? String(item["summary"]) : null;
  const url = item["url"] ? String(item["url"]) : null;
  return (
    <article className="news-card">
      <header>
        <span className="news-title">{title}</span>
      {Boolean(date) && <span className="badge">{date}</span>}
      </header>
      {Boolean(summary) && <p className="news-summary">{summary}</p>}
      {Boolean(url) && (
        <p className="muted news-source">
          source: <code>{url}</code>
        </p>
      )}
    </article>
  );
}

function CommitteeTable({ rows }: { rows: Record<string, unknown>[] }) {
  if (rows.length === 0) return <p className="muted">(none identified)</p>;
  return (
    <table className="mini-table">
      <thead>
        <tr>
          <th>Role</th>
          <th>Name</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={i}>
            <td>{String(row["role"] ?? "—")}</td>
            <td>{String(row["name_if_known"] ?? row["name"] ?? "not available")}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function SignalList({ items }: { items: Record<string, unknown>[] }) {
  if (items.length === 0) return <p className="muted">(no signals)</p>;
  return (
    <ul className="signal-list">
      {items.map((s, i) => (
        <li key={i}>
          <span>{String(s["signal"] ?? "")}</span>
          {Boolean(s["source"]) && (
            <span className="muted signal-source">source: <code>{String(s["source"])}</code></span>
          )}
        </li>
      ))}
    </ul>
  );
}

function StringList({ items }: { items: string[] }) {
  if (items.length === 0) return <p className="muted">(none)</p>;
  return (
    <ul className="bullet-list">
      {items.map((it, i) => (
        <li key={i}>{it}</li>
      ))}
    </ul>
  );
}

function FlatKeyValues({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data);
  if (entries.length === 0) return <p className="muted">(empty)</p>;
  return (
    <dl className="kv">
      {entries.map(([k, v]) => (
        <div key={k}>
          <dt>{humanise(k)}</dt>
          <dd>
            <GenericValue fieldKey={k} value={v} />
          </dd>
        </div>
      ))}
    </dl>
  );
}

function CitationsList({ items }: { items: Record<string, unknown>[] }) {
  if (items.length === 0) return <p className="muted">(no citations)</p>;
  return (
    <ul className="citation-list">
      {items.map((c, i) => (
        <li key={i}>
          <code className="citation-url">{String(c["url"] ?? "—")}</code>
          {Boolean(c["quote"]) && <span className="citation-quote">"{String(c["quote"])}"</span>}
        </li>
      ))}
    </ul>
  );
}

// Routes a (key, value) pair to the most specific renderer available.
function GenericValue({ fieldKey, value }: { fieldKey: string; value: unknown }) {
  if (value === null || value === undefined || value === "") {
    return <span className="muted">not available</span>;
  }
  if (typeof value === "string") {
    // URL-ish: render as code
    if (/^(https?:\/\/|document:)/.test(value)) return <code>{value}</code>;
    return <>{value}</>;
  }
  if (typeof value === "number" || typeof value === "boolean") return <>{String(value)}</>;
  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="muted">(none)</span>;
    if (isStringArray(value)) return <StringList items={value} />;
    if (value.every(isRecord)) {
      // Detect known nested-array shapes by their first item's keys.
      const sample = value[0] as Record<string, unknown>;
      const keys = new Set(Object.keys(sample));
      if (fieldKey === "recent_news" || (keys.has("title") && keys.has("summary"))) {
        return (
          <div className="news-list">
            {(value as Record<string, unknown>[]).map((it, i) => (
              <NewsItem key={i} item={it} />
            ))}
          </div>
        );
      }
      if (fieldKey === "buying_committee" || (keys.has("role") && (keys.has("name_if_known") || keys.has("name")))) {
        return <CommitteeTable rows={value as Record<string, unknown>[]} />;
      }
      if (fieldKey === "signal_evidence" || (keys.has("signal") && keys.has("source"))) {
        return <SignalList items={value as Record<string, unknown>[]} />;
      }
      if (fieldKey === "citations" || (keys.has("url") && keys.has("quote"))) {
        return <CitationsList items={value as Record<string, unknown>[]} />;
      }
      // Generic record array: render each as a small kv card.
      return (
        <div className="record-list">
          {(value as Record<string, unknown>[]).map((row, i) => (
            <div key={i} className="record-card">
              <FlatKeyValues data={row} />
            </div>
          ))}
        </div>
      );
    }
    // Mixed array: comma-separated.
    return <>{value.map((v) => String(v)).join(", ")}</>;
  }
  if (isRecord(value)) {
    return <FlatKeyValues data={value} />;
  }
  return <code>{String(value)}</code>;
}

// ---------------------------------------------------------------------------
// Section blocks — each consumes a top-level briefing field.
// ---------------------------------------------------------------------------

function ExecutiveSummary({ items }: { items: string[] | undefined }) {
  if (!items) return null;
  if (items.length === 0) return <p className="muted">(awaiting synthesis)</p>;
  return (
    <ul className="bullet-list">
      {items.map((line, i) => (
        <li key={i}>{line}</li>
      ))}
    </ul>
  );
}

function NextSteps({ items }: { items: string[] | undefined }) {
  if (!items) return null;
  if (items.length === 0) return <p className="muted">(awaiting synthesis)</p>;
  return (
    <ol className="bullet-list">
      {items.map((line, i) => (
        <li key={i}>{line}</li>
      ))}
    </ol>
  );
}

// ---------------------------------------------------------------------------
// Main panel
// ---------------------------------------------------------------------------

// Map worker_id -> briefing field name. Confirmed against
// SalesResearchWorkflow._aggregate (workflow.py):
//   account_planner       -> account_profile
//   icp_fit_analyst       -> icp_fit
//   competitive_context   -> competitive_play
//   outreach_personalizer -> recommended_outreach
const WORKER_TO_SECTION: Record<string, {
  key: "account_profile" | "icp_fit" | "competitive_play" | "recommended_outreach";
  label: string;
  workerLabel: string;
}> = {
  account_planner: {
    key: "account_profile",
    label: "Account profile",
    workerLabel: "researching company news, signals, and buying committee",
  },
  icp_fit_analyst: {
    key: "icp_fit",
    label: "ICP fit",
    workerLabel: "scoring fit against your ICP",
  },
  competitive_context: {
    key: "competitive_play",
    label: "Competitive play",
    workerLabel: "mapping competitor presence and differentiators",
  },
  outreach_personalizer: {
    key: "recommended_outreach",
    label: "Recommended outreach",
    workerLabel: "drafting outreach for the persona",
  },
};

const SECTION_ORDER: Array<keyof typeof WORKER_TO_SECTION> = [
  "account_planner",
  "icp_fit_analyst",
  "competitive_context",
  "outreach_personalizer",
];

export function ResultPanel({ briefing, events }: Props) {
  const [showRaw, setShowRaw] = useState(false);

  // Extract per-section data from worker partials so we can render
  // sections progressively as they arrive — without waiting for the
  // supervisor synthesis. Once ``briefing`` is set, it takes
  // precedence (the supervisor may have refined the ordering).
  const partialsByWorker = useMemo(() => {
    const map: Record<string, unknown> = {};
    for (const e of events) {
      if (e.type === "partial") map[e.worker_id] = e.output;
    }
    return map;
  }, [events]);

  // Nothing to show until at least one partial OR the briefing arrives.
  const hasAnything = briefing !== null || Object.keys(partialsByWorker).length > 0;
  if (!hasAnything) return null;

  function dataFor(workerId: keyof typeof WORKER_TO_SECTION): unknown | null {
    const sectionKey = WORKER_TO_SECTION[workerId].key;
    if (briefing) return briefing[sectionKey];
    return partialsByWorker[workerId] ?? null;
  }

  return (
    <div className="card">
      <div className="result-header">
        <h2>
          Briefing
          {!briefing && <span className="muted briefing-progress"> — assembling…</span>}
        </h2>
        <label className="raw-toggle">
          <input
            type="checkbox"
            checked={showRaw}
            onChange={(e) => setShowRaw(e.target.checked)}
          />
          Show raw JSON
        </label>
      </div>

      {showRaw ? (
        <pre className="raw-json">
          {JSON.stringify(briefing ?? partialsByWorker, null, 2)}
        </pre>
      ) : (
        <>
          <Section id="section-summary" title="Executive summary" data={briefing?.executive_summary}>
            {briefing ? (
              <ExecutiveSummary items={briefing.executive_summary} />
            ) : (
              <SectionLoader label="Executive summary" subLabel="waiting on supervisor synthesis" />
            )}
          </Section>

          {SECTION_ORDER.map((workerId) => {
            const meta = WORKER_TO_SECTION[workerId];
            const data = dataFor(workerId);
            return (
              <Section key={workerId} id={`section-${workerId}`} title={meta.label} data={data}>
                {data && isRecord(data) ? (
                  <FlatKeyValues data={data} />
                ) : (
                  <SectionLoader label={meta.label} subLabel={meta.workerLabel} />
                )}
              </Section>
            );
          })}

          <Section id="section-next_steps" title="Next steps" data={briefing?.next_steps}>
            {briefing ? (
              <NextSteps items={briefing.next_steps} />
            ) : (
              <SectionLoader label="Next steps" subLabel="waiting on supervisor synthesis" />
            )}
          </Section>

          {briefing?.usage && (
            <Section title="Usage">
              <FlatKeyValues data={briefing.usage as Record<string, unknown>} />
            </Section>
          )}
        </>
      )}
    </div>
  );
}
