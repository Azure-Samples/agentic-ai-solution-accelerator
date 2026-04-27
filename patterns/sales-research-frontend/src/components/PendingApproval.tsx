interface PendingApproval {
  tool: string;
  args: Record<string, unknown>;
}

interface Props {
  approvals: PendingApproval[];
}

// Renders proposed side-effect tool calls when no HITL approver is
// configured. The framing is "suggested next action — requires
// approval", NOT "error" — the lab/starter intentionally fails open
// to a preview rather than auto-executing destructive writes.
//
// Partner forks plug their own approver (Teams adaptive card, Jira
// ticket, custom queue) by setting ``HITL_APPROVER_ENDPOINT`` on the
// backend; once set, these events stop being emitted and you'll see
// ``tool_result`` / ``tool_error`` instead.
export function PendingApproval({ approvals }: Props) {
  if (approvals.length === 0) return null;
  return (
    <section
      id="section-approvals"
      className="result-section pending-approvals"
      aria-label="Pending approvals"
    >
      <header className="section-header">
        <h3>Suggested next actions</h3>
        <span className="section-sub">
          {approvals.length} action{approvals.length === 1 ? "" : "s"} ready for human approval
        </span>
      </header>
      <div className="approvals-list">
        {approvals.map((a, i) => (
          <article key={i} className="approval-card">
            <header>
              <code className="approval-tool">{a.tool}</code>
              <span className="badge warn">Requires approval</span>
            </header>
            <p className="approval-help">
              The supervisor proposes this side-effect. It was <strong>not executed</strong>{" "}
              because no HITL approver is configured. Wire one up via{" "}
              <code>HITL_APPROVER_ENDPOINT</code> to enable controlled execution.
            </p>
            <dl className="kv approval-args">
              {Object.entries(a.args).map(([k, v]) => (
                <div key={k}>
                  <dt>{k.replace(/_/g, " ")}</dt>
                  <dd>
                    {typeof v === "string" ? v : <code>{JSON.stringify(v)}</code>}
                  </dd>
                </div>
              ))}
            </dl>
          </article>
        ))}
      </div>
    </section>
  );
}
