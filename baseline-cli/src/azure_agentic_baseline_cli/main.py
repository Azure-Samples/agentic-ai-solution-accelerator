"""baseline CLI — Phase A stub.

Commands (Phase B):
  baseline validate-spec <spec.agent.yaml>
  baseline doctor
  baseline materialize [params | evals | dashboards | alerts | all]
  baseline new-customer-repo <name> --bundle <bundle> [--scenario <name>]
  baseline upgrade [--plan <target> | --apply <plan>]
"""

import typer

app = typer.Typer(help="Azure Agentic AI Solution Accelerator CLI.")


@app.callback()
def main() -> None:
    """baseline — accelerator CLI."""


if __name__ == "__main__":
    app()
