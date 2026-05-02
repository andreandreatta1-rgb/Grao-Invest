param(
  [string]$RepoRoot = "",
  [int]$UserId = 1,
  [int]$FlushRetries = 120
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
  $RepoRoot = Split-Path -Parent $PSScriptRoot
}

$logDir = Join-Path $RepoRoot "data\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = Join-Path $logDir ("b3_automation_" + $stamp + ".log")

function Invoke-Step {
  param(
    [string]$Title,
    [string[]]$ArgList,
    [switch]$AllowFailure
  )
  "[$(Get-Date -Format o)] START $Title" | Tee-Object -FilePath $logFile -Append
  Push-Location $RepoRoot
  try {
    $null = (& py -3 @ArgList 2>&1 | Tee-Object -FilePath $logFile -Append)
    $code = $LASTEXITCODE
  } finally {
    Pop-Location
  }
  if ($code -ne 0 -and -not $AllowFailure) {
    throw "$Title falhou com exit code $code"
  }
  "[$(Get-Date -Format o)] END $Title (exit=$code)" | Tee-Object -FilePath $logFile -Append
  return $code
}

$dailyArgs = @(
  "scripts/run_b3_daily_job.py",
  "--user-id", "$UserId",
  "--full-universe",
  "--flush-max-retries", "$FlushRetries"
)

$skipBuildArgs = @(
  "scripts/run_b3_daily_job.py",
  "--user-id", "$UserId",
  "--skip-build",
  "--flush-max-retries", "$FlushRetries"
)

$publishArgs = @("scripts/publish_dashboard_seed.py")

$runCode = 0
try {
  $runCode = [int](Invoke-Step -Title "run_b3_daily_job(full)" -ArgList $dailyArgs)
} catch {
  "[$(Get-Date -Format o)] WARN tentativa full falhou: $($_.Exception.Message)" | Tee-Object -FilePath $logFile -Append
  $runCode = [int](Invoke-Step -Title "run_b3_daily_job(skip-build retry)" -ArgList $skipBuildArgs -AllowFailure)
}

if ($runCode -ne 0) {
  "[$(Get-Date -Format o)] ERROR job diario nao concluiu; publish nao executado" | Tee-Object -FilePath $logFile -Append
  exit $runCode
}

$publishCode = [int](Invoke-Step -Title "publish_dashboard_seed" -ArgList $publishArgs -AllowFailure)
if ($publishCode -ne 0) {
  "[$(Get-Date -Format o)] WARN publish falhou (sem bloquear ciclo)" | Tee-Object -FilePath $logFile -Append
}

"[$(Get-Date -Format o)] DONE ciclo completo" | Tee-Object -FilePath $logFile -Append
exit 0
