---
description: Run scripts/explain-change.py against the current branch to preflight which lint rules will fire, which evals will run, and what the deploy pipeline will do on the next azd up. Use before opening a PR or squash-merging.
tools: ['codebase', 'runCommands']
---

# /explain-change — preflight a diff before you commit or push

Use this when you want a quick, structured readout of what's going to happen in CI for the change on the current branch. It is a READ-ONLY preflight — it does NOT run the lint, the evals, or the deploy pipeline. CI gates remain authoritative.

## When to use
- Before opening a PR, to know which lint rules to expect to pass/fail.
- Before squash-merging into `main`, to double-check which parts of the deploy pipeline will re-run.
- When a partner changes something and wonders "is this going to block CI?".
- When reviewing a PR and you want a structured list of "what does this touch".

## Invocation

```bash
# Diff vs main (most common)
python scripts/explain-change.py

# Diff vs a specific ref (e.g. origin/main, a feature branch base, or a tag)
python scripts/explain-change.py --base origin/main

# One-line summary only
python scripts/explain-change.py --quiet

# Machine-readable JSON (for tools / follow-up scripting)
python scripts/explain-change.py --json
```

The script inspects committed diff vs base + staged + unstaged + untracked files. Every file is matched against a static catalog of glob patterns; each category carries an impact block naming the specific `@check` functions in `scripts/accelerator-lint.py` and the evals that will run.

## What the output covers
For each affected category, the report names:
- **lint**: which `accelerator-lint.py` rules evaluate the change
- **evals**: which eval runners (quality, redteam) will exercise the change
- **deploy**: what the next `azd up` or workflow run does with this change
- **partner guardrails**: e.g. "don't add Azure envs by hand-editing `deploy.yml`", "keep `agents/__init__.py` scaffold-managed"

And a tailored **Recommended pre-commit** command list — always includes `python scripts/accelerator-lint.py`, plus an import smoke test when Python source changed, plus round-trip scaffolder / YAML parse checks when the change touches those surfaces.

## Example conversations

**Partner:** "I added a new worker agent via `scaffold-agent.py`. What happens next?"
→ Run `/explain-change`. Expect the `agent-three-layer`, `agents-init`, and `scenario-workflow` categories to fire, with impact text that reminds them to (a) paste the YAML snippet into `accelerator.yaml`, (b) add the agent id to a golden case's `exercises[]`, (c) run the suggested pre-commit commands before they push.

**Partner:** "I tweaked the bicep for a bigger model capacity. Safe?"
→ Run `/explain-change`. Expect `infra-bicep` to fire with the reminder that `azd up` will re-provision and `no_preview_api_versions` + `bicep_has_content_filter` still need to pass.

**Partner:** "I edited `deploy.yml` directly to add a customer env."
→ Run `/explain-change`. Expect `deploy-workflow` to fire with the explicit guardrail "never add Azure envs by hand-editing this file; use `/deploy-to-env` + `deploy/environments.yaml`". They can back out before the `deploy_matrix_matches_azure_envs` lint blocks the PR.

## Guardrails
- `/explain-change` is a preflight, not a gate. A clean report does not mean CI will pass; run `python scripts/accelerator-lint.py` to actually check.
- The category catalog in `scripts/explain-change.py` is maintained by hand. If a new lint rule is added to `accelerator-lint.py` that does not appear in the catalog's impact text, update it in the same commit.
- If the report categorizes something unexpectedly (or marks it "uncategorized"), that's a signal the catalog is out of date — surface it rather than ignore it.
