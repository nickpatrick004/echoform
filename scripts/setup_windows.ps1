# Echoform Windows setup script.
# Run from the repository root in PowerShell:
#   powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
#
# By default this reuses an existing .venv. Use -RecreateVenv to delete and rebuild it.

param(
    [switch]$RecreateVenv
)

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

Write-Host "== Echoform setup =="

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Error "ffmpeg was not found on PATH. Install FFmpeg and reopen PowerShell."
}

$pythonCandidates = @("py -3.12", "py -3.11", "py -3.10", "python")
$pythonCmd = $null

foreach ($candidate in $pythonCandidates) {
    try {
        $version = & $candidate.Split()[0] $candidate.Split()[1..10] -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" 2>$null
        $pythonCmd = $candidate
        break
    } catch {}
}

if (-not $pythonCmd) {
    Write-Error "Python 3.10+ was not found. Install Python 3.12 from python.org."
}

Write-Host "Using Python command: $pythonCmd"
Write-Host "Using FFmpeg: $((ffmpeg -version)[0])"

if ((Test-Path ".venv") -and $RecreateVenv) {
    Write-Host "Removing old .venv because -RecreateVenv was supplied"
    Remove-Item -Recurse -Force ".venv"
}

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment"
    $parts = $pythonCmd.Split()
    & $parts[0] $parts[1..10] -m venv .venv
} else {
    Write-Host "Reusing existing .venv"
}

.\.venv\Scripts\Activate.ps1

Write-Host "Installing Echoform in editable mode"
python -m pip install --upgrade pip
python -m pip install -e .

Write-Host "Verifying install"
python -c "import echoform; print('echoform package:', echoform.__file__)"
echoform --help | Out-Null
echoform-queue --help | Out-Null

Write-Host ""
Write-Host "Setup complete."
Write-Host "Activate later with: .\.venv\Scripts\Activate.ps1"
Write-Host "Rebuild the venv with: powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1 -RecreateVenv"
Write-Host "Run a preview with: echoform-queue --folder batch --preview"
Write-Host "Run full batch with: echoform-queue --folder batch"
