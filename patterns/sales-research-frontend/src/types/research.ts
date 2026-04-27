// Mirror of `src/scenarios/sales_research/schema.py::ResearchRequest`.
// Keep in sync with the backend pydantic schema.
export interface ResearchRequest {
  company_name: string;
  domain: string;
  seller_intent: string;
  persona: string;
  icp_definition: string;
  our_solution: string;
  context_hints: string[];
}

// Aggregated supervisor output — see
// `src/scenarios/sales_research/agents/supervisor/transform.py`.
export interface ResearchBriefing {
  executive_summary: string[];
  account_profile: Record<string, unknown>;
  icp_fit: Record<string, unknown>;
  competitive_play: Record<string, unknown>;
  recommended_outreach: Record<string, unknown>;
  next_steps: string[];
  requires_approval: string[];
  tool_args: Record<string, Record<string, unknown>>;
  usage?: Record<string, number>;
}

// SSE event shapes emitted by `SalesResearchWorkflow.stream` and
// `SupervisorDAG.run` — see src/workflow/supervisor.py and
// src/scenarios/sales_research/workflow.py.
//
// Event ordering contract:
//   status (supervisor.routed)
//   partial × N (one per worker)
//   status (aggregating)
//   briefing_ready                ← briefing renderable; stream NOT terminal
//   [tool_skipped | tool_result | tool_error] × M
//   final                         ← terminal; carries the same briefing
//
// `error` is reserved for FATAL failures (DAG aborts, aggregation throws).
// Side-effect tool failures use `tool_error` and do NOT abort the stream.
export type StreamEvent =
  | { type: "status"; stage: string; stages?: string[][] }
  | { type: "partial"; worker_id: string; output: unknown }
  | { type: "worker_skipped"; worker_id: string; error?: string; reason?: string }
  | { type: "briefing_ready"; briefing: ResearchBriefing }
  | { type: "tool_skipped"; tool: string; reason: string }
  | { type: "tool_result"; tool: string; result: unknown }
  | { type: "tool_error"; tool: string; error: string }
  | { type: "final"; briefing: ResearchBriefing }
  | { type: "error"; message: string };
