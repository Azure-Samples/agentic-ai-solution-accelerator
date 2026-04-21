"""Sales Research & Outreach workflow — Supervisor + parallel workers.

Graph::

    [request]
        |
        v
    supervisor (plan) -----------+
        |                        |
        v                        |
    +--------+----------+--------+
    |        |          |        |
    v        v          v        v
  account  icp_fit   competitive  outreach  (parallel)
  planner  analyst   context      personalizer
    |        |          |         |
    +--------+-----+----+---------+
                   v
               aggregator
                   |
           requires_approval?
               +----+-----+
               v          v
           HITL gate    done
               |
               v
          side-effect tools

The aggregator composes the Supervisor's final briefing and then (if the
supervisor flagged any side-effect tools in ``requires_approval``) drives the
HITL checkpoint and invokes the tool. Foundry holds the system instructions
of each agent; this code never materialises agent instructions.
"""
from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator

from azure.identity import DefaultAzureCredential

# The Agent Framework SDK supplies these. We import lazily inside the
# executor to keep test startup cheap.
try:
    from agent_framework.azure import AzureAIClient  # type: ignore
    from agent_framework import WorkflowBuilder  # type: ignore  # noqa: F401
except Exception:  # pragma: no cover - SDK may not be installed in lint envs
    AzureAIClient = None  # type: ignore
    WorkflowBuilder = None  # type: ignore

from src.accelerator_baseline.killswitch import assert_enabled
from src.accelerator_baseline.telemetry import Event, emit_event
from src.tools import SIDE_EFFECT_TOOLS
from src.workflow.base import BaseWorkflow

from .agents import (
    account_planner,
    competitive_context,
    icp_fit_analyst,
    outreach_personalizer,
    supervisor,
)


class SalesResearchWorkflow:
    """Facade over the Agent Framework WorkflowBuilder.

    In this scaffold, the workflow is executed as a plain asyncio fan-out. A
    partner swapping to Agent Framework WorkflowBuilder only changes this
    class; the agents and tools are unchanged.
    """

    def __init__(self, *, primary_index_name: str = "accounts") -> None:
        self._credential = DefaultAzureCredential()
        self._primary_index_name = primary_index_name

    async def stream(self, request: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        assert_enabled("workflow")
        emit_event(Event(name="request.received",
                         args_redacted={"company": request["company_name"]}))

        # 1. Supervisor plans (scopes which workers to run for this request).
        yield {"type": "status", "stage": "supervisor.planning"}
        plan = await self._invoke_agent(
            supervisor.AGENT_NAME, supervisor.build_prompt(request)
        )

        # 2. Account Planner runs FIRST - downstream workers need the real
        #    account profile. Retrieval grounding is attached here so the
        #    agent can cite from the configured index.
        yield {"type": "status", "stage": "account_planner"}
        grounding_chunks = await self._retrieve_grounding(request["company_name"])
        account_profile = await self._run_worker(
            account_planner,
            {"company_name": request["company_name"],
             "domain": request.get("domain", ""),
             "context_hints": request.get("context_hints", []),
             "grounding_chunks": grounding_chunks},
        )
        yield {"type": "partial", "account_profile": account_profile}

        # 3. ICP-Fit and Competitive-Context run in parallel.
        yield {"type": "status", "stage": "workers.parallel"}
        icp, comp = await asyncio.gather(
            self._run_worker(
                icp_fit_analyst,
                {"account_profile": account_profile,
                 "icp_definition": request["icp_definition"]},
            ),
            self._run_worker(
                competitive_context,
                {"account_profile": account_profile,
                 "our_solution": request["our_solution"]},
            ),
        )

        # 4. Outreach Personalizer depends on all three earlier outputs.
        yield {"type": "status", "stage": "outreach_personalizer"}
        outreach = await self._run_worker(
            outreach_personalizer,
            {"account_profile": account_profile,
             "fit_summary": icp,
             "competitive_context": comp,
             "persona": request.get("persona", "Decision maker")},
        )
        yield {"type": "partial", "icp": icp, "competitive": comp,
               "outreach": outreach}

        # 5. Aggregator: re-invoke supervisor with all worker outputs.
        yield {"type": "status", "stage": "aggregating"}
        final = await self._aggregate(
            request, account_profile, icp, comp, outreach, plan
        )

        # 6. Optional side-effect tools. HITL enforced inside tool modules.
        approvals_needed = final.get("requires_approval", [])
        tool_args_map = final.get("tool_args", {}) or {}
        for tool_name in approvals_needed:
            if tool_name not in SIDE_EFFECT_TOOLS:
                continue
            fn, _schema = SIDE_EFFECT_TOOLS[tool_name]
            args = tool_args_map.get(tool_name, {})
            if not args:
                yield {"type": "tool_skipped", "tool": tool_name,
                       "reason": "no tool_args produced by supervisor"}
                continue
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

    async def _retrieve_grounding(self, query: str) -> list[dict[str, Any]]:
        """Pull top-K grounded chunks from the scenario's primary AI Search index.

        Fails open to an empty list when retrieval isn't configured (so the
        unit-test stub path still works); the agent's validator enforces
        that any factual claim has a citation.
        """
        try:
            from src.retrieval.ai_search import SearchRetriever
        except Exception:
            return []
        try:
            retriever = SearchRetriever(self._primary_index_name)
        except Exception:
            return []
        try:
            chunks = await retriever.search(query, top=5)
            return [
                {"id": c.id, "content": c.content, "source": c.source,
                 "score": c.score}
                for c in chunks
            ]
        except Exception as exc:
            emit_event(Event(name="retrieval.returned", ok=False, error=str(exc)))
            return []
        finally:
            try:
                await retriever.close()
            except Exception:
                pass

    async def _aggregate(self, request, account_profile, icp, comp, outreach,
                         plan) -> dict[str, Any]:
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


def build_workflow(context: Any) -> BaseWorkflow:
    """Scenario workflow factory.

    Signature matches the contract in ``src.workflow.registry``:
    ``build_workflow(ScenarioContext) -> BaseWorkflow``. The context exposes
    ``retrieval_indexes``; we pick the first declared index as the primary
    grounding source so partners can rename without editing this file.
    """
    indexes = getattr(context, "retrieval_indexes", ()) or ()
    primary = indexes[0].name if indexes else "accounts"
    return SalesResearchWorkflow(primary_index_name=primary)
