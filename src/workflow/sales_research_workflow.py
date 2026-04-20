"""Sales Research & Outreach workflow — Supervisor + parallel workers.

Graph:

    [request]
        │
        ▼
    supervisor (plan) ──────────────┐
        │                           │
        ▼                           │
    ┌────────┬──────────┬──────────┤
    │        │          │          │
    ▼        ▼          ▼          ▼
  account  icp_fit   competitive  outreach  (parallel)
  researcher analyst  context      personalizer
    │        │          │          │
    └────────┴─────┬────┴──────────┘
                   ▼
              aggregator
                   │
          requires_approval?
              ┌────┴─────┐
              ▼          ▼
           HITL gate    done
              │
              ▼
         side-effect tools
         (crm_write_contact,
          send_email)

The aggregator composes the Supervisor's final briefing and then (if the
supervisor flagged any side-effect tools in ``requires_approval``) drives the
HITL checkpoint and invokes the tool. The agent framework's ``WorkflowBuilder``
is used here — Foundry holds the system instructions of each agent; this code
never materialises agent instructions.
"""
from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator

from azure.identity import DefaultAzureCredential

# The Agent Framework SDK supplies these. We import lazily inside the
# executor to keep test startup cheap.
try:
    from agent_framework.azure import AzureAIClient  # type: ignore
    from agent_framework import WorkflowBuilder  # type: ignore
except Exception:  # pragma: no cover — SDK may not be installed in lint envs
    AzureAIClient = None  # type: ignore
    WorkflowBuilder = None  # type: ignore

from ..accelerator_baseline.hitl import checkpoint
from ..accelerator_baseline.killswitch import assert_enabled
from ..accelerator_baseline.telemetry import Event, emit_event
from ..agents import (
    account_researcher,
    competitive_context,
    icp_fit_analyst,
    outreach_personalizer,
    supervisor,
)
from ..tools import SIDE_EFFECT_TOOLS


class SalesResearchWorkflow:
    """Facade over the Agent Framework WorkflowBuilder.

    In this scaffold, the workflow is executed as a plain asyncio fan-out. A
    partner swapping to Agent Framework WorkflowBuilder only changes this
    class; the agents and tools are unchanged.
    """

    def __init__(self) -> None:
        self._credential = DefaultAzureCredential()

    async def stream(self, request: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        assert_enabled("workflow")
        emit_event(Event(name="request.received",
                         args_redacted={"company": request["company_name"]}))

        # 1. Supervisor plans (returns a context the workers share).
        yield {"type": "status", "stage": "supervisor.planning"}
        plan = await self._invoke_agent(
            supervisor.AGENT_NAME, supervisor.build_prompt(request)
        )

        account_profile: dict[str, Any] = {}
        # 2. Parallel worker fan-out.
        yield {"type": "status", "stage": "workers.parallel"}
        acct, icp, comp = await asyncio.gather(
            self._run_worker(
                account_researcher, {"company_name": request["company_name"],
                                     "domain": request.get("domain", ""),
                                     "context_hints": request.get("context_hints", [])},
            ),
            self._run_worker(
                icp_fit_analyst, {"account_profile": "<placeholder>",
                                  "icp_definition": request["icp_definition"]},
            ),
            self._run_worker(
                competitive_context, {"account_profile": "<placeholder>",
                                      "our_solution": request["our_solution"]},
            ),
        )
        account_profile = acct

        outreach = await self._run_worker(
            outreach_personalizer,
            {"account_profile": account_profile,
             "fit_summary": icp,
             "competitive_context": comp,
             "persona": request.get("persona", "Decision maker")},
        )
        yield {"type": "partial", "account_profile": account_profile,
               "icp": icp, "competitive": comp, "outreach": outreach}

        # 3. Aggregator: re-invoke supervisor with all worker outputs to
        #    compose the final briefing (Foundry instructions define the
        #    synthesis behaviour).
        yield {"type": "status", "stage": "aggregating"}
        final = await self._aggregate(
            request, account_profile, icp, comp, outreach, plan
        )

        # 4. Optional side-effect tools with HITL.
        approvals_needed = final.get("requires_approval", [])
        for tool_name in approvals_needed:
            if tool_name not in SIDE_EFFECT_TOOLS:
                continue
            fn, schema = SIDE_EFFECT_TOOLS[tool_name]
            args = final.get("tool_args", {}).get(tool_name, {})
            await checkpoint(tool=tool_name, args=args, policy="always",
                             reviewer_context={"briefing": final})
            result = await fn(**args)
            yield {"type": "tool_result", "tool": tool_name, "result": result}

        emit_event(Event(name="response.returned", ok=True))
        yield {"type": "final", "briefing": final}

    # ---- internals --------------------------------------------------------
    async def _invoke_agent(self, agent_name: str, prompt: str) -> str:
        """Retrieve a Foundry agent and run one turn. Stubbed if SDK absent."""
        if AzureAIClient is None:
            emit_event(Event(name="worker.completed",
                             args_redacted={"agent": agent_name, "stub": True}))
            return "{}"
        client = AzureAIClient(agent_name=agent_name, use_latest_version=True)
        agent = client.as_agent()
        result = await agent.run(prompt)
        return result.text

    async def _run_worker(self, module: Any, request: dict[str, Any]) -> dict[str, Any]:
        raw = await self._invoke_agent(module.AGENT_NAME, module.build_prompt(request))
        data = module.transform_response(raw or "{}")
        ok, err = module.validate_response(data)
        if not ok:
            emit_event(Event(name="worker.completed", ok=False, error=err,
                             external_system=module.AGENT_NAME))
            raise ValueError(f"{module.AGENT_NAME}: {err}")
        emit_event(Event(name="worker.completed", ok=True,
                         external_system=module.AGENT_NAME))
        return data

    async def _aggregate(self, request, account_profile, icp, comp, outreach,
                         plan) -> dict[str, Any]:
        # Supervisor synthesises worker outputs.
        synthesis_prompt = supervisor.build_prompt(request) + (
            f"\n\nWORKER OUTPUTS:\n"
            f"account_profile = {account_profile}\n"
            f"icp_fit = {icp}\n"
            f"competitive = {comp}\n"
            f"outreach = {outreach}\n"
        )
        raw = await self._invoke_agent(supervisor.AGENT_NAME, synthesis_prompt)
        data = supervisor.transform_response(raw or "{}")
        ok, err = supervisor.validate_response(data)
        if not ok:
            raise ValueError(f"supervisor aggregator: {err}")
        return data
