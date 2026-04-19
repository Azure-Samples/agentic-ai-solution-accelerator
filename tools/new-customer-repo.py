"""new-customer-repo.py — Phase A stub.

Scaffolds a new customer engagement repo:
  - Copies azd-templates/<bundle>/ into the target repo.
  - Initializes baseline.lock.yaml pinned to current supported release.
  - Drops CODEOWNERS templates (customer-sponsor team + partner-lead team).
  - Drops branch-protection GH Actions workflow to bootstrap protection on main.
  - Drops qualify.yml workflow for OIDC-signed qualification.
  - Enforces isolation prerequisites for sandbox profile (see docs/supported-customization-boundary.md §2).

Phase B will implement full logic.
"""

import sys
from pathlib import Path


def main() -> int:
    print("Phase A stub: new-customer-repo <name> --bundle <bundle>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
