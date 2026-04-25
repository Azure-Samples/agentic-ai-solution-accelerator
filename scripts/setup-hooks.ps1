[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

if ($PSVersionTable.PSVersion.Major -lt 7) {
    throw "PowerShell 7+ is required on Windows because azd hooks use 'pwsh'. Install PowerShell 7, then rerun: pwsh -File scripts/setup-hooks.ps1"
}

$RepoRoot = Split-Path -Parent $PSScriptRoot
$HooksDir = Join-Path $RepoRoot ".azd-hooks"
$VenvDir = Join-Path $HooksDir ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$ReadyFile = Join-Path $HooksDir ".ready"
$RequirementsFile = Join-Path $RepoRoot "requirements-hooks.txt"

function Write-Status {
    param([string]$Name, [string]$Detail)
    Write-Host ("{0,-18} {1}" -f $Name, $Detail)
}

function Require-Command {
    param([string]$Name, [string]$Hint)
    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $cmd) { throw "$Name not found on PATH. $Hint" }
    return $cmd
}

function Parse-Version {
    param([string]$Text, [string]$Name)
    if ($Text -match '(\d+\.\d+\.\d+)') {
        return [version]$matches[1]
    }
    throw "Could not parse $Name version from: $Text"
}

function Assert-MinVersion {
    param(
        [string]$Name,
        [version]$Minimum,
        [scriptblock]$GetText
    )
    $text = & $GetText
    $actual = Parse-Version -Text "$text" -Name $Name
    if ($actual -lt $Minimum) {
        throw "$Name $actual is too old. Need >= $Minimum."
    }
    Write-Status $Name "ok ($actual)"
}

Write-Host "Validating local prerequisites for azd hook venv..."
Require-Command -Name "git" -Hint "Install Git and reopen your terminal." | Out-Null
Assert-MinVersion -Name "git" -Minimum ([version]"2.0.0") -GetText { git --version }

Require-Command -Name "az" -Hint "Install Azure CLI >= 2.55." | Out-Null
Assert-MinVersion -Name "az" -Minimum ([version]"2.55.0") -GetText { (az --version 2>&1 | Select-String -Pattern '^azure-cli' | Select-Object -First 1).Line }

Require-Command -Name "azd" -Hint "Install Azure Developer CLI >= 1.10." | Out-Null
Assert-MinVersion -Name "azd" -Minimum ([version]"1.10.0") -GetText { azd version }

Require-Command -Name "gh" -Hint "Install GitHub CLI >= 2.50." | Out-Null
Assert-MinVersion -Name "gh" -Minimum ([version]"2.50.0") -GetText { gh version }

$pyCmd = Get-Command "python" -ErrorAction SilentlyContinue
if (-not $pyCmd) { $pyCmd = Get-Command "python3" -ErrorAction SilentlyContinue }
if (-not $pyCmd) {
    throw "No 'python' or 'python3' on PATH. Install Python 3.11+ (python.org, winget, or activate a Conda env), then rerun."
}
if ($pyCmd.Source -like "*\Microsoft\WindowsApps\*") {
    throw "PATH resolves to the Microsoft Store Python alias stub ($($pyCmd.Source)). Install a real Python 3.11+ from python.org / winget / Conda, then rerun."
}

$BasePython = $pyCmd.Source
$verText = & $BasePython --version 2>&1
if ($LASTEXITCODE -ne 0 -or "$verText" -notmatch '^Python (\d+\.\d+\.\d+)') {
    throw "Could not parse Python version from: $verText"
}
$pythonVersion = [version]$matches[1]
if ($pythonVersion -lt [version]"3.11.0") {
    throw "Python $pythonVersion is too old. Need >= 3.11."
}
Write-Status "python" "ok ($pythonVersion at $BasePython)"

if (-not (Test-Path -LiteralPath $RequirementsFile)) {
    throw "Missing $RequirementsFile"
}

$env:REQ_FILE = $RequirementsFile
$RequirementsSha = (& $BasePython -c "import hashlib, os, pathlib; print(hashlib.sha256(pathlib.Path(os.environ['REQ_FILE']).read_bytes()).hexdigest())").Trim()

$Rebuild = $true
if ((Test-Path -LiteralPath $ReadyFile) -and (Test-Path -LiteralPath $VenvPython)) {
    try {
        $Ready = Get-Content -LiteralPath $ReadyFile -Raw | ConvertFrom-Json
        if (
            $Ready.python_exe -eq $BasePython -and
            $Ready.python_version -eq $pythonVersion.ToString() -and
            $Ready.requirements_sha256 -eq $RequirementsSha
        ) {
            $Rebuild = $false
        }
    } catch {
        $Rebuild = $true
    }
}

New-Item -ItemType Directory -Force -Path $HooksDir | Out-Null

if ($Rebuild) {
    if (Test-Path -LiteralPath $VenvDir) {
        Remove-Item -LiteralPath $VenvDir -Recurse -Force
    }

    Write-Host "Creating repo-local hook venv..."
    & $BasePython -m venv $VenvDir
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $VenvPython)) {
        throw "Failed to create venv at $VenvDir. If your machine blocks venv creation, use a machine policy exception or a supported prebuilt environment."
    }

    Write-Host "Installing hook dependencies..."
    & $VenvPython -m pip install --disable-pip-version-check -r $RequirementsFile
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to install hook dependencies. If your org blocks PyPI, configure PIP_INDEX_URL / proxy settings, then rerun."
    }

    @{
        python_exe = $BasePython
        python_version = $pythonVersion.ToString()
        requirements_sha256 = $RequirementsSha
        ready_at = [DateTime]::UtcNow.ToString("o")
    } | ConvertTo-Json | Set-Content -LiteralPath $ReadyFile -Encoding UTF8

    Write-Status "hooks venv" "created"
} else {
    Write-Status "hooks venv" "ready (cached)"
}

Write-Host ""
Write-Host "Hook environment is ready. Next step: azd up"
