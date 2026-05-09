param(
  [string]$DashboardUrl = "https://grao-invest.vercel.app/api/dashboard/summary/1",
  [int]$Attempts = 3,
  [int]$TimeoutSeconds = 90,
  [switch]$SkipNetwork
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$VenvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
  $Python = $VenvPython
} else {
  $Python = "python"
}

$Args = @(
  "scripts\run_grao_quality_gate.py",
  "--frontend-dist",
  "services\api\frontend_dist",
  "--attempts",
  "$Attempts",
  "--timeout-seconds",
  "$TimeoutSeconds",
  "--json"
)

if (-not $SkipNetwork) {
  $Args += @("--dashboard-url", $DashboardUrl)
}

Push-Location $RepoRoot
try {
  & $Python @Args
  if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
  }
} finally {
  Pop-Location
}
