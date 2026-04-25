#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

HOOKS_DIR="$REPO_ROOT/.azd-hooks"
VENV_DIR="$HOOKS_DIR/.venv"
VENV_PY="$VENV_DIR/bin/python"
READY_FILE="$HOOKS_DIR/.ready"
REQ_FILE="$REPO_ROOT/requirements-hooks.txt"

say() {
  printf '%-18s %s\n' "$1" "$2"
}

fail() {
  printf 'ERROR: %s\n' "$1" >&2
  exit 1
}

extract_semver() {
  printf '%s\n' "$1" | grep -Eo '[0-9]+\.[0-9]+\.[0-9]+' | head -n 1
}

version_ge() {
  v1=$1
  v2=$2

  old_ifs=$IFS
  IFS=.
  set -- $v1
  a1=${1:-0}; a2=${2:-0}; a3=${3:-0}
  set -- $v2
  b1=${1:-0}; b2=${2:-0}; b3=${3:-0}
  IFS=$old_ifs

  [ "$a1" -gt "$b1" ] && return 0
  [ "$a1" -lt "$b1" ] && return 1
  [ "$a2" -gt "$b2" ] && return 0
  [ "$a2" -lt "$b2" ] && return 1
  [ "$a3" -ge "$b3" ]
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "$2"
}

json_field() {
  READY_FILE="$READY_FILE" FIELD="$1" "$PYTHON_EXE" -c '
import json, os, pathlib
p = pathlib.Path(os.environ["READY_FILE"])
if not p.exists():
    print("")
else:
    data = json.loads(p.read_text(encoding="utf-8"))
    print(data.get(os.environ["FIELD"], ""))
'
}

printf 'Validating local prerequisites for azd hook venv...\n'

require_cmd git "git not found on PATH. Install Git and reopen your terminal."
GIT_VERSION=$(extract_semver "$(git --version 2>/dev/null || true)")
[ -n "$GIT_VERSION" ] || fail "Could not parse git version."
say "git" "ok ($GIT_VERSION)"

require_cmd az "Azure CLI not found on PATH. Install Azure CLI >= 2.55."
AZ_VERSION=$(extract_semver "$(az --version 2>/dev/null | grep -E '^azure-cli' | head -n 1 || true)")
[ -n "$AZ_VERSION" ] || fail "Could not parse Azure CLI version."
version_ge "$AZ_VERSION" "2.55.0" || fail "Azure CLI $AZ_VERSION is too old. Need >= 2.55.0."
say "az" "ok ($AZ_VERSION)"

require_cmd azd "Azure Developer CLI not found on PATH. Install azd >= 1.10."
AZD_VERSION=$(extract_semver "$(azd version 2>/dev/null || true)")
[ -n "$AZD_VERSION" ] || fail "Could not parse azd version."
version_ge "$AZD_VERSION" "1.10.0" || fail "azd $AZD_VERSION is too old. Need >= 1.10.0."
say "azd" "ok ($AZD_VERSION)"

require_cmd gh "GitHub CLI not found on PATH. Install gh >= 2.50."
GH_VERSION=$(extract_semver "$(gh version 2>/dev/null || true)")
[ -n "$GH_VERSION" ] || fail "Could not parse gh version."
version_ge "$GH_VERSION" "2.50.0" || fail "gh $GH_VERSION is too old. Need >= 2.50.0."
say "gh" "ok ($GH_VERSION)"

require_cmd python3 "python3 not found on PATH. Install Python 3.11+ (python.org, your distro's package manager, or activate a Conda env), then rerun."
PYTHON_EXE=$(command -v python3)
PYTHON_VERSION=$(extract_semver "$(python3 --version 2>/dev/null || true)")
[ -n "$PYTHON_VERSION" ] || fail "Could not parse python3 version."
version_ge "$PYTHON_VERSION" "3.11.0" || fail "python3 $PYTHON_VERSION is too old. Need >= 3.11.0."
say "python3" "ok ($PYTHON_VERSION)"

[ -f "$REQ_FILE" ] || fail "Missing $REQ_FILE"

REQ_SHA=$(REQ_FILE="$REQ_FILE" "$PYTHON_EXE" -c '
import hashlib, os, pathlib
print(hashlib.sha256(pathlib.Path(os.environ["REQ_FILE"]).read_bytes()).hexdigest())
')

REBUILD=1
if [ -f "$READY_FILE" ] && [ -x "$VENV_PY" ]; then
  CURRENT_EXE=$(json_field python_exe)
  CURRENT_VER=$(json_field python_version)
  CURRENT_SHA=$(json_field requirements_sha256)

  if [ "$CURRENT_EXE" = "$PYTHON_EXE" ] && \
     [ "$CURRENT_VER" = "$PYTHON_VERSION" ] && \
     [ "$CURRENT_SHA" = "$REQ_SHA" ]; then
    REBUILD=0
  fi
fi

mkdir -p "$HOOKS_DIR"

if [ "$REBUILD" -eq 1 ]; then
  rm -rf "$VENV_DIR"

  printf 'Creating repo-local hook venv...\n'
  "$PYTHON_EXE" -m venv "$VENV_DIR" || fail "Failed to create venv at $VENV_DIR."

  [ -x "$VENV_PY" ] || fail "Venv python missing after creation: $VENV_PY"

  printf 'Installing hook dependencies...\n'
  "$VENV_PY" -m pip install --disable-pip-version-check -r "$REQ_FILE" || fail "Failed to install hook dependencies. If your org blocks PyPI, configure PIP_INDEX_URL / proxy settings, then rerun."

  READY_FILE="$READY_FILE" PYTHON_EXE="$PYTHON_EXE" PYTHON_VERSION="$PYTHON_VERSION" REQ_SHA="$REQ_SHA" "$PYTHON_EXE" -c '
import json, os, pathlib
from datetime import datetime, timezone

payload = {
    "python_exe": os.environ["PYTHON_EXE"],
    "python_version": os.environ["PYTHON_VERSION"],
    "requirements_sha256": os.environ["REQ_SHA"],
    "ready_at": datetime.now(timezone.utc).isoformat(),
}
pathlib.Path(os.environ["READY_FILE"]).write_text(json.dumps(payload), encoding="utf-8")
'
  say "hooks venv" "created"
else
  say "hooks venv" "ready (cached)"
fi

printf '\nHook environment is ready. Next step: azd up\n'
