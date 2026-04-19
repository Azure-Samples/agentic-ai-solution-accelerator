# actioning-prod — azd template

Production bundle for solutions with side-effect tools (mutating customer systems beyond read).

## Prerequisites
- Bundle = `actioning-prod`; profile = `prod-standard`.
- Spec validates via `python tools/validate-spec.py`.
- T2 required in customer repo `pyproject.toml`: `baseline-drift`, `baseline-feedback`, `baseline-hitl`, `baseline-actions`.
- Every side-effect tool declared in Spec with `side_effect: true` + a HITL point defined on the agent that invokes it.
- RAI scoping minutes + Impact Assessment signed off — with explicit coverage of side-effect tool risks.

## Quickstart
```bash
azd init --template <accelerator-feed>/actioning-prod@0.1.0
azd up
```

## Gotchas
- Validator fails closed if any side-effect tool lacks HITL wiring. Fix the Spec + code; don't disable the validator.
- Kill-switch enforcement is non-negotiable; covered in [`../../../.github/copilot-instructions.md`](../../../.github/copilot-instructions.md) MUST #5.
- HITL default placement is `before_action`. Weaker placements require explicit customer sign-off + heightened telemetry.

## Supportability
Community best-effort per [`../../../SUPPORT.md`](../../../SUPPORT.md). Partner owns the customer pager — side-effect incidents are especially the partner's responsibility.
