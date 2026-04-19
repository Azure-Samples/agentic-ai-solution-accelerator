# actioning-prod — azd template

Production bundle for solutions with side-effect tools (mutate customer data, invoke customer systems beyond read).

## Prerequisites
- Path B qualification complete.
- Bundle = `actioning-prod`; profile = `prod-standard`.
- T2 required: `baseline-drift`, `baseline-feedback`, `baseline-hitl`, `baseline-actions`.
- Every side-effect tool declared in Spec with `side_effect: true` + HITL point defined.

## Quickstart
```bash
azd init --template agentic-ai-accelerator/actioning-prod@0.1.0
azd up
```

## Gotchas
- Validator fails closed if any side-effect tool lacks HITL wiring.
- Kill-switch enforcement is non-negotiable; covered in `copilot-instructions.md` MUST #4.
