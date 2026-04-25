import { useState } from "react";
import type { ResearchBriefing } from "../types/research";

interface Props {
  briefing: ResearchBriefing | null;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="result-section">
      <h3>{title}</h3>
      {children}
    </section>
  );
}

function KeyValueBlock({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data);
  if (entries.length === 0) return <p className="muted">(empty)</p>;
  return (
    <dl className="kv">
      {entries.map(([k, v]) => (
        <div key={k}>
          <dt>{k}</dt>
          <dd>
            {typeof v === "string" ? v : <pre>{JSON.stringify(v, null, 2)}</pre>}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function ResultPanel({ briefing }: Props) {
  const [showRaw, setShowRaw] = useState(false);
  if (!briefing) return null;

  return (
    <div className="card">
      <div className="result-header">
        <h2>Briefing</h2>
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
        <pre className="raw-json">{JSON.stringify(briefing, null, 2)}</pre>
      ) : (
        <>
          <Section title="Executive summary">
            <ul>
              {briefing.executive_summary.map((line, i) => (
                <li key={i}>{line}</li>
              ))}
            </ul>
          </Section>
          <Section title="Account profile">
            <KeyValueBlock data={briefing.account_profile} />
          </Section>
          <Section title="ICP fit">
            <KeyValueBlock data={briefing.icp_fit} />
          </Section>
          <Section title="Competitive play">
            <KeyValueBlock data={briefing.competitive_play} />
          </Section>
          <Section title="Recommended outreach">
            <KeyValueBlock data={briefing.recommended_outreach} />
          </Section>
          <Section title="Next steps">
            <ol>
              {briefing.next_steps.map((step, i) => (
                <li key={i}>{step}</li>
              ))}
            </ol>
          </Section>
          {briefing.requires_approval.length > 0 && (
            <Section title="Pending HITL approvals">
              <ul>
                {briefing.requires_approval.map((tool) => (
                  <li key={tool}>
                    <code>{tool}</code>
                    <pre>
                      {JSON.stringify(briefing.tool_args[tool] ?? {}, null, 2)}
                    </pre>
                  </li>
                ))}
              </ul>
            </Section>
          )}
          {briefing.usage && (
            <Section title="Usage">
              <KeyValueBlock data={briefing.usage as Record<string, unknown>} />
            </Section>
          )}
        </>
      )}
    </div>
  );
}
