"""new-customer-repo.py — Phase A stub.

Scaffolds a new customer engagement repo:
  - Copies examples/azd-templates/<bundle>/ into the target repo's infra/.
  - Copies examples/scenarios/<scenario>/ into src/ as starting code.
  - Drops .github/copilot-instructions.md + .github/chatmodes/ (Copilot IDE kit).
  - Drops .github/workflows/validate.yml running validate-spec on every PR.
  - Drops CODEOWNERS stub.
  - Pins azure-agentic-baseline + required T2 packages per bundle in pyproject.toml.
  - Places a spec.agent.yaml skeleton at repo root.

Phase B will implement full logic.
"""

import sys
from pathlib import Path


def main() -> int:
    print("Phase A stub: new-customer-repo <name> --bundle <bundle>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
