"""baseline CLI — Phase A stub.

Commands (Phase B):
  baseline doctor [--preflight <target>]
  baseline reconcile [--pre-upgrade]
  baseline upgrade [--plan <target> | --apply <plan> | --rollback]
  baseline migrate [--plan <target> | --apply | --status]
  baseline materialize [params | evals | dashboards | alerts | all]
  baseline attest [--capture | --issue]
  baseline deploy --verify <attestation-id>
  baseline waive [--propose | --list | --renew]
  baseline sbom [--emit | --verify]
  baseline new-customer-repo <name> --bundle <bundle>
"""

import typer

app = typer.Typer(help="Azure Agentic AI Solution Accelerator CLI.")


@app.callback()
def main() -> None:
    """baseline — accelerator CLI."""


if __name__ == "__main__":
    app()
