# find-python.ps1 — locate a real Python 3 interpreter on Windows for azd hooks.
#
# Why this exists:
# azd spawns a fresh pwsh subshell for hooks. On Windows, calling 'python'
# from that subshell often resolves to the Microsoft Store App Execution
# Alias stub (which prints "Python was not found" and exits 9009) instead
# of the real interpreter, even when conda/venv is active in the parent
# shell. This script probes the common install paths (python.org launcher,
# python.exe on PATH, python3.exe), explicitly skips any candidate living
# under \WindowsApps\ (the Store stub directory), and emits the absolute
# path of a working Python 3 interpreter on stdout.
#
# Usage from a hook:
#   $py = (& "$PWD/scripts/find-python.ps1").Trim()
#   & $py scripts/sync-models-from-manifest.py

$ErrorActionPreference = 'Stop'

function Test-PythonCandidate {
    param([string]$Cmd, [string[]]$LauncherArgs = @())
    $g = Get-Command $Cmd -ErrorAction SilentlyContinue
    if (-not $g) { return $null }
    # Reject Microsoft Store App Execution Alias stub.
    if ($g.Source -and ($g.Source -like '*\WindowsApps\*')) { return $null }
    try {
        $ver = & $Cmd @LauncherArgs --version 2>&1
        if ($LASTEXITCODE -ne 0) { return $null }
        if ("$ver" -notmatch 'Python 3') { return $null }
        # For 'py' launcher, resolve to the actual interpreter path so
        # downstream callers invoke it directly (avoids re-launcher overhead
        # and ensures sys.executable is stable for any subprocess work).
        if ($Cmd -eq 'py') {
            $exe = & $Cmd @LauncherArgs -c "import sys; print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $exe) { return $exe.Trim() }
        }
        return $g.Source
    } catch {
        return $null
    }
}

$candidates = @(
    @{ Cmd = 'py';      Args = @('-3') },
    @{ Cmd = 'python';  Args = @()     },
    @{ Cmd = 'python3'; Args = @()     }
)

foreach ($c in $candidates) {
    $exe = Test-PythonCandidate -Cmd $c.Cmd -LauncherArgs $c.Args
    if ($exe) {
        Write-Output $exe
        exit 0
    }
}

Write-Error @"
No working Python 3 interpreter was found on PATH.

The accelerator hooks need a real Python 3.11+ interpreter (not the
Microsoft Store App Execution Alias stub). Install one of:

  - python.org installer:  https://www.python.org/downloads/
  - winget:                winget install Python.Python.3.11
  - Anaconda/Miniconda:    https://docs.conda.io/en/latest/miniconda.html

If you already have Python installed, ensure its directory comes before
%LOCALAPPDATA%\Microsoft\WindowsApps in PATH, OR disable the Store
aliases at: Settings > Apps > Advanced app settings > App execution
aliases > toggle off python.exe and python3.exe.
"@
exit 1
