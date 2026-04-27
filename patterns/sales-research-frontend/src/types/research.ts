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
// Stream protocol
// ---------------
// Every event carries a monotonic ``seq`` (assigned by ``src/main.py``).
// The stream ALWAYS terminates with ``{type:"done"}`` — a missing
// ``done`` means the connection was cut by an intermediary and the
// client should surface that to the user, NOT treat the partial output
// as a successful (degraded) response.
//
// Heartbeats are SSE protocol-level comment lines (``: ka\n\n``) and
// never reach this handler, so there is no ``heartbeat`` data variant.
//
// ``stream_interrupted`` is a synthetic event the FRONTEND CLIENT emits
// when the response body ends without a ``done`` event. It is not sent
// by the backend.
//
// Event ordering contract:
//   status (supervisor.routed)
//   worker_started × N  ← one per worker as it is dispatched (so the
//                         frontend can show a per-worker placeholder
//                         immediately instead of waiting for the first
//                         token, which can take 5-15s on cold replicas)
//   chunk × *           ← interleaved with all other events while
//                         workers / aggregator are streaming tokens
//   partial × N         ← one per worker (final accumulated output)
//   status (aggregating)
//   chunk × *           ← supervisor LLM streaming during _aggregate
//   briefing_ready      ← briefing renderable; stream NOT terminal
//   [tool_skipped | tool_pending_approval | tool_result | tool_error] × M
//   final               ← briefing carrier; stream NOT terminal
//   done                ← terminal; stream is over
//
// ``error`` is reserved for FATAL failures (DAG aborts, aggregation
// throws). Side-effect tool failures use ``tool_error`` and do NOT
// abort the stream. ``tool_pending_approval`` is what the lab/starter
// emits when no HITL approver is configured — the proposed action is
// surfaced for review without being executed.
type WithSeq<T> = T & { seq?: number };
export type StreamEvent =
  | WithSeq<{ type: "status"; stage: string; stages?: string[][] }>
  | WithSeq<{ type: "worker_started"; worker_id: string; agent: string }>
  | WithSeq<{ type: "chunk"; agent: string; worker_id?: string | null; delta: string }>
  | WithSeq<{ type: "partial"; worker_id: string; output: unknown }>
  | WithSeq<{ type: "worker_skipped"; worker_id: string; error?: string; reason?: string }>
  | WithSeq<{ type: "briefing_ready"; briefing: ResearchBriefing }>
  | WithSeq<{ type: "tool_skipped"; tool: string; reason: string }>
  | WithSeq<{ type: "tool_pending_approval"; tool: string; args: Record<string, unknown> }>
  | WithSeq<{ type: "tool_result"; tool: string; result: unknown }>
  | WithSeq<{ type: "tool_error"; tool: string; error: string }>
  | WithSeq<{ type: "final"; briefing: ResearchBriefing }>
  | WithSeq<{ type: "error"; message: string }>
  | WithSeq<{ type: "done" }>
  | { type: "stream_interrupted"; last_seq: number; last_event?: string };

