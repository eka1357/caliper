# Caliper tasks for Windows PowerShell. Same targets as the Makefile.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\tasks.ps1 <target> [-Clip path] [-GateM metres]
# Targets marked $ spend API credits; run them only when you mean to.

param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet("setup", "dev-api", "dev-web", "test", "lint", "baseline", "eval", "field",
        "ablation", "study", "report")]
    [string]$Target,
    [string]$Clip,
    [string]$GateM
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Py = Join-Path $Root "backend\.venv\Scripts\python.exe"
$Backend = Join-Path $Root "backend"
$Web = Join-Path $Root "web"

function Invoke-Step {
    param([string]$Dir, [string]$Exe, [string[]]$StepArgs)
    Push-Location $Dir
    try {
        & $Exe @StepArgs
        if ($LASTEXITCODE -ne 0) { throw "$Exe $($StepArgs -join ' ') failed with exit code $LASTEXITCODE" }
    }
    finally { Pop-Location }
}

function Test-Web { return Test-Path (Join-Path $Web "package.json") }

function Write-Spend { Write-Host "`$ This target spends API credits." -ForegroundColor Yellow }

switch ($Target) {
    "setup" {
        Invoke-Step $Backend "python" @("-m", "venv", ".venv")
        Invoke-Step $Backend $Py @("-m", "pip", "install", "-e", ".[dev]")
        if (Test-Web) { Invoke-Step $Web "npm" @("install") } else { Write-Host "web/ not created yet; skipping npm install" }
    }
    "dev-api" { Invoke-Step $Backend $Py @("-m", "uvicorn", "caliper.api:app", "--reload", "--port", "8000") }
    "dev-web" { Invoke-Step $Web "npm" @("run", "dev") }
    "test" {
        Invoke-Step $Backend $Py @("-m", "pytest", "-q")
        if (Test-Web) { Invoke-Step $Web "npx" @("tsc", "--noEmit") } else { Write-Host "web/ not created yet; skipping typecheck" }
    }
    "lint" {
        Invoke-Step $Root $Py @("-m", "ruff", "check", "backend", "eval", "scripts")
        Invoke-Step $Root $Py @("-m", "ruff", "format", "--check", "backend", "eval", "scripts")
        if (Test-Web) { Invoke-Step $Web "npm" @("run", "lint") } else { Write-Host "web/ not created yet; skipping eslint" }
    }
    # $ Muse Spark alone on QuantiPhy validation (Phase 0)
    "baseline" { Write-Spend; Invoke-Step $Root $Py @("eval/baseline.py") }
    # $ Caliper on QuantiPhy validation: dev, holdout, full
    "eval" { Write-Spend; Invoke-Step $Root $Py @("eval/quantiphy.py", "--splits", "dev", "holdout", "full") }
    # $ Caliper on our field clips
    "field" { Write-Spend; Invoke-Step $Root $Py @("eval/field.py") }
    # $ Rule-parser and audit-off ablations on QuantiPhy validation
    "ablation" { Write-Spend; Invoke-Step $Root $Py @("eval/ablation.py", "--splits", "dev", "holdout", "full") }
    # $ Street speed study on one clip, e.g. tasks.ps1 study -Clip data/field/S01.mp4 -GateM 10.0
    "study" {
        if (-not $Clip -or -not $GateM) { throw "study needs -Clip and -GateM" }
        Write-Spend
        Invoke-Step $Root $Py @("-m", "caliper.study", "--clip", $Clip, "--gate-m", $GateM)
    }
    # Free: rebuild results.csv, web/public/results.json and the README table from saved outputs
    "report" { Invoke-Step $Root $Py @("eval/report.py") }
}
