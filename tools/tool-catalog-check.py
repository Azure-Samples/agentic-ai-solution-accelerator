"""tool-catalog-check.py — Phase A stub.

Verifies every tool referenced in spec.agent.yaml is in the Foundry tool catalog
permitted for the declared bundle. prod-privatelink bundles have a restricted
catalog (subset).

Phase B will implement full logic against docs/foundry-tool-catalog.md.
"""

import sys


def main() -> int:
    print("Phase A stub: tool-catalog-check <spec.agent.yaml> <bundle>")
    return 0


if __name__ == "__main__":
    sys.exit(main())
