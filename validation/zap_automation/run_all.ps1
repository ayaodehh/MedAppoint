#Requires -Version 5.1
<#
    Wrapper for the MedAppoint ZAP automation harness.
    Stops on the first failure.
#>

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = "python"

function Banner($title) {
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host " $title" -ForegroundColor Cyan
    Write-Host "================================================================" -ForegroundColor Cyan
}

function Run-Step($label, $script) {
    Banner $label
    & $python (Join-Path $here $script)
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[run_all] step '$label' failed with exit code $LASTEXITCODE." -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

if (-not (Test-Path (Join-Path $here ".env"))) {
    Write-Host "[run_all] missing .env; copy .env.example to .env first and set ZAP_API_KEY." -ForegroundColor Red
    exit 1
}

Run-Step "Step 1/3 - seed test users"        "seed_users.py"
Run-Step "Step 2/3 - drive app through ZAP"  "drive_app.py"
Run-Step "Step 3/3 - active scan + report"   "run_active_scan.py"

Banner "All done"
Write-Host "Reports:"
Write-Host "  validation/zap/zap_active.html"
Write-Host "  validation/zap/zap_active_summary.txt"
