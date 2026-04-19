"""validate-repo.py — Phase A stub.

Repo-level conformance check. Verifies:
  - spec.agent.yaml present + validates (delegates to validate-spec.py)
  - baseline packages pinned per bundle (T1 core + required T2)
  - CODEOWNERS present
  - CI workflow runs validate-spec on PRs
  - materialized files unedited (DO-NOT-EDIT headers match hashes)
  - override files validate against override schemas
  - no forbidden patterns (inline secrets, kill-switch bypass, cost-tracker disable,
    direct model SDK calls bypassing baseline.foundry_client)

Phase B will implement full logic.
"""

import sys
from pathlib import Path


def main() -> int:
    repo = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    print(f"Phase A stub: would validate repo at {repo.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
