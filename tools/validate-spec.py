"""validate-spec.py — Phase A stub.

Validates a customer repo's spec.agent.yaml against delivery-assets/schema/spec.schema.json.
Emits classified errors: block (fail close) / warn / info.

Phase B will implement full logic. For now, this file establishes the surface.
"""

import json
import sys
from pathlib import Path

import jsonschema
import yaml


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: validate-spec.py <spec.agent.yaml>", file=sys.stderr)
        return 2

    spec_path = Path(sys.argv[1])
    schema_path = Path(__file__).parent.parent / "delivery-assets" / "schema" / "spec.schema.json"

    spec = yaml.safe_load(spec_path.read_text())
    schema = json.loads(schema_path.read_text())

    try:
        jsonschema.validate(instance=spec, schema=schema)
    except jsonschema.ValidationError as e:
        print(f"BLOCK: {e.message} @ {'/'.join(str(p) for p in e.absolute_path)}", file=sys.stderr)
        return 1

    # Phase B: add cross-field rules (bundle↔profile, side_effect↔bundle, etc.)
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
