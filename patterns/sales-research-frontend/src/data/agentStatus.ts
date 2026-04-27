// Per-worker status copy for the live "thinking" panel.
//
// During a worker's 30-60s gpt-5-mini call we receive a stream of chunk
// events but no structured progress. Showing the raw model tail was
// noisy (JSON fragments) and unhelpful. Instead we rotate through a
// short script of human-readable phases per agent. The rotation index
// is derived from the accumulated chunk-text length so it advances
// roughly in step with how much the model has produced — no timer
// required, and it pauses naturally if the model stalls.

export const AGENT_PHASES: Record<string, string[]> = {
  account_planner: [
    "Researching recent news, leadership moves, and funding signals…",
    "Pulling grounded citations from Foundry / Azure AI Search…",
    "Synthesizing the account profile and key facts…",
  ],
  icp_fit_analyst: [
    "Mapping the buying committee and likely stakeholders…",
    "Scoring ICP fit signals against your definition…",
    "Drafting evidence and citations for each signal…",
  ],
  competitive_context: [
    "Identifying likely incumbents and adjacent vendors…",
    "Surfacing differentiators against the competitive field…",
    "Drafting objection handlers for the most common pushback…",
  ],
  outreach_personalizer: [
    "Crafting opener hooks tied to the account's recent moves…",
    "Tailoring talking points to the target persona…",
    "Writing the recommended next-touch and call-to-action…",
  ],
  supervisor: [
    "Aggregating worker outputs into a single briefing…",
    "Drafting the executive summary and next steps…",
    "Finalizing approvals and side-effect tool arguments…",
  ],
};

const FALLBACK = ["Working…", "Still working…", "Almost there…"];

// Rough thresholds (in chunk-text characters) for advancing through the
// 3 phases. Calibrated for gpt-5-mini outputs that tend to land in the
// 1.5-6 kB range; values are intentionally generous so we don't churn.
const PHASE_BOUNDARIES = [400, 1800];

export function statusForAgent(agentId: string, accumulatedChars: number): string {
  const phases = AGENT_PHASES[agentId] ?? FALLBACK;
  let idx = 0;
  for (const boundary of PHASE_BOUNDARIES) {
    if (accumulatedChars >= boundary) idx += 1;
  }
  return phases[Math.min(idx, phases.length - 1)];
}

// Friendly display name for the agent label. Falls back to the raw id
// (snake_case) if we don't have a mapping — preferable to silently
// hiding an unknown worker.
export const AGENT_LABEL: Record<string, string> = {
  account_planner: "Account planner",
  icp_fit_analyst: "ICP fit analyst",
  competitive_context: "Competitive context",
  outreach_personalizer: "Outreach personalizer",
  supervisor: "Supervisor",
};

export function labelForAgent(agentId: string): string {
  return AGENT_LABEL[agentId] ?? agentId;
}
