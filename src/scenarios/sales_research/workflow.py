"""Sales Research & Outreach workflow — Supervisor DAG over four workers.

Graph (declared once as ``WORKERS`` below; the DAG scheduler infers stages
from ``depends_on`` and streams partials as each worker completes)::

    [request]
        v
    account_planner (grounded)
        v
    +-----+------+
    v            v
    icp_fit   competitive
    analyst   context
    +-----+------+
        v
    outreach_personalizer
        v
    supervisor aggregator  ->  HITL gate  ->  side-effect tools

The scenario facade is intentionally thin: a fresh ``WorkerState`` per
request (so concurrent callers never share mutable state), plus an
aggregator + side-effect driver around the DAG. Adding, swapping, or
parallelising a worker is a data change to ``WORKERS``; the scaffolder in
``scripts/scaffold-agent.py`` rewrites this dict directly.
"""
from __future__ import annotations

from typing import Any, AsyncIterator

from azure.identity import DefaultAzureCredential

try:
    from agent_framework.azure import AzureAIClient  # type: ignore
except Exception:  # pragma: no cover - SDK may not be installed in lint envs
    AzureAIClient = None  # type: ignore

from src.accelerator_baseline.killswitch import assert_enabled
from src.accelerator_baseline.telemetry import Event, emit_event
from src.tools import SIDE_EFFECT_TOOLS
from src.workflow.base import BaseWorkflow
from src.workflow.supervisor import SupervisorDAG, WorkerSpec, WorkerState

from .agents import (
    account_planner,
    competitive_context,
    icp_fit_analyst,
    outreach_personalizer,
    supervisor,
)


# ---------------------------------------------------------------------------
# Worker input builders — module-level ``def`` so ``scripts/scaffold-agent.py``
# can append new named functions and register them in ``WORKERS`` via a single
# AST rewrite. Do NOT inline as lambdas.
# ---------------------------------------------------------------------------
def _grounding_query_account_planner(state: WorkerState) -> str:
    return state.request["company_name"]


def _build_input_account_planner(state: WorkerState) -> dict[str, Any]:
    return {
        "company_name": state.request["company_name"],
        "domain": state.request.get("domain", ""),
        "context_hints": state.request.get("context_hints", []),
        "grounding_chunks": state.grounding_chunks.get("account_planner", []),
    }


def _build_input_icp_fit_analyst(state: WorkerState) -> dict[str, Any]:
    return {
        "account_profile": state.outputs["account_planner"],
        "icp_definition": state.request["icp_definition"],
    }


def _build_input_competitive_context(state: WorkerState) -> dict[str, Any]:
    return {
        "account_profile": state.outputs["account_planner"],
        "our_solution": state.request["our_solution"],
    }


def _build_input_outreach_personalizer(state: WorkerState) -> dict[str, Any]:
    return {
        "account_profile": state.outputs["account_planner"],
        "fit_summary": state.outputs["icp_fit_analyst"],
        "competitive_context": state.outputs["competitive_context"],
        "persona": state.request.get("persona", "Decision maker"),
    }


WORKERS: dict[str, WorkerSpec] = {
    "account_planner": WorkerSpec(
        id="account_planner",
        module=account_planner,
        build_input=_build_input_account_planner,
        grounding_query=_grounding_query_account_planner,
    ),
    "icp_fit_analyst": WorkerSpec(
        id="icp_fit_analyst",
        module=icp_fit_analyst,
        build_input=_build_input_icp_fit_analyst,
        depends_on=frozenset({"account_planner"}),
    ),
    "competitive_context": WorkerSpec(
        id="competitive_context",
        module=competitive_context,
        build_input=_build_input_competitive_context,
        depends_on=frozenset({"account_planner"}),
    ),
    "outreach_personalizer": WorkerSpec(
        id="outreach_personalizer",
        module=outreach_personalizer,
        build_input=_build_input_outreach_personalizer,
        depends_on=frozenset(
            {"account_planner", "icp_fit_analyst", "competitive_context"}
        ),
    ),
}


class SalesResearchWorkflow:
    """Thin scenario facade over :class:`SupervisorDAG`.

    The DAG is constructed (and validated) once at workflow build time so
    a malformed ``WORKERS`` dict fails at FastAPI startup rather than on
    first request.
    """

    def __init__(self, *, primary_index_name: str = "accounts") -> None:
        self._credential = DefaultAzureCredential()
        self._primary_index_name = primary_index_name
        self._dag = SupervisorDAG(
            WORKERS,
            invoke_agent=self._invoke_agent,
            retrieve=self._retrieve_grounding,  # pyright: ignore[reportArgumentType]  # bound method matches Retrieve protocol at runtime
        )

    async def stream(self, request: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        assert_enabled("workflow")
        emit_event(
            Event(
                name="request.received",
                args_redacted={"company": request["company_name"]},
            )
        )

        state = WorkerState(request=request)

        async for evt in self._dag.run(state):
            yield evt  # pyright: ignore[reportReturnType]  # Mapping widens to dict at runtime via dict ops downstream

        yield {"type": "status", "stage": "aggregating"}
        final = await self._aggregate(request, state.outputs)

        if state.usage_totals:
            final.setdefault("usage", dict(state.usage_totals))

        approvals_needed = final.get("requires_approval", []) or []
        tool_args_map = final.get("tool_args", {}) or {}
        for tool_name in approvals_needed:
            if tool_name not in SIDE_EFFECT_TOOLS:
                continue
            fn, _schema = SIDE_EFFECT_TOOLS[tool_name]
            args = tool_args_map.get(tool_name, {})
            if not args:
                yield {
                    "type": "tool_skipped",
                    "tool": tool_name,
                    "reason": "no tool_args produced by supervisor",
                }
                continue
            result = await fn(**args)
            yield {"type": "tool_result", "tool": tool_name, "result": result}

        emit_event(Event(name="response.returned", ok=True))
        yield {"type": "final", "briefing": final}

    # ---- internals --------------------------------------------------------
    async def _invoke_agent(
        self, agent_name: str, prompt: str, state: WorkerState
    ) -> str:
        """Retrieve a Foundry agent and run one turn. Accumulates token usage
        into ``state.usage_totals`` — never on ``self`` — so concurrent
        requests do not corrupt each other's cost totals.
        """
        if AzureAIClient is None:
            emit_event(
                Event(
                    name="worker.completed",
                    args_redacted={"agent": agent_name, "stub": True},
                )
            )
            return "{}"
        client = AzureAIClient(agent_name=agent_name, use_latest_version=True)
        agent = client.as_agent()
        result = await agent.run(prompt)
        usage = getattr(result, "usage", None)
        if usage is not None:
            for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                val = getattr(usage, key, None)
                if isinstance(val, (int, float)):
                    state.usage_totals[key] = (
                        state.usage_totals.get(key, 0) + int(val)
                    )
            state.usage_totals["agent_calls"] = (
                state.usage_totals.get("agent_calls", 0) + 1
            )
        return result.text

    async def _retrieve_grounding(self, query: str) -> list[dict[str, Any]]:
        """Pull top-K grounded chunks from the scenario's primary AI Search index.

        Fails open (empty list) when retrieval isn't configured so the unit-
        test stub path still works; agent validators enforce citations.
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
                {
                    "id": c.id,
                    "content": c.content,
                    "source": c.source,
                    "score": c.score,
                }
                for c in chunks
            ]
        except Exception as exc:
            emit_event(Event(name="retrieval.returned", ok=False, error=str(exc)))
            return []
        finally:
            try:
                await retriever.close()
            except Exception:  # noqa: S110  # best-effort cleanup in finally
                pass

    async def _aggregate(
        self, request: dict[str, Any], outputs: dict[str, Any]
    ) -> dict[str, Any]:
        synthesis_prompt = supervisor.build_prompt(request) + (
            f"\n\nWORKER OUTPUTS:\n"
            f"account_profile = {outputs.get('account_planner')}\n"
            f"icp_fit = {outputs.get('icp_fit_analyst')}\n"
            f"competitive = {outputs.get('competitive_context')}\n"
            f"outreach = {outputs.get('outreach_personalizer')}\n"
        )
        # Aggregator runs outside the DAG and does not accumulate token usage
        # into any particular worker's budget; a transient WorkerState is
        # threaded through ``_invoke_agent`` only so the usage counters roll
        # up into the final briefing's ``usage`` field.
        raw = await self._invoke_agent(
            supervisor.AGENT_NAME, synthesis_prompt, WorkerState(request=request)
        )
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

