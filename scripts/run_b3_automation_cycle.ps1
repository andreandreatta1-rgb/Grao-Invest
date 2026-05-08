param(
  [string]$RepoRoot = "",
  [int]$UserId = 1,
  [int]$FlushRetries = 120,
  [int]$CurrentRecentBarsWindow = 2000,
  [int]$CryptoLookbackHours = 72,
  [int]$B3RefreshMaxDaysPerInstrument = 10,
  [switch]$SkipFeedRefresh,
  [switch]$SkipCurrentTheses,
  [switch]$SkipOpsGuard
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
  $RepoRoot = Split-Path -Parent $PSScriptRoot
}

$logDir = Join-Path $RepoRoot "data\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = Join-Path $logDir ("b3_automation_" + $stamp + ".log")

$venvPython = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$pythonExe = if (Test-Path $venvPython) { $venvPython } else { "python" }

function Write-Log {
  param([string]$Message)
  $Message | Tee-Object -FilePath $logFile -Append | Out-Host
}

function ConvertTo-ProcessArgument {
  param([string]$Value)
  if ($Value -match '[\s"]') {
    return '"' + ($Value -replace '"', '\"') + '"'
  }
  return $Value
}

function Invoke-Step {
  param(
    [string]$Title,
    [string[]]$ArgList,
    [switch]$AllowFailure
  )
  Write-Log "[$(Get-Date -Format o)] START $Title"
  $stdoutFile = Join-Path $logDir ("step_" + $stamp + "_" + ($Title -replace '[^\w.-]', '_') + ".out.log")
  $stderrFile = Join-Path $logDir ("step_" + $stamp + "_" + ($Title -replace '[^\w.-]', '_') + ".err.log")
  $arguments = ($ArgList | ForEach-Object { ConvertTo-ProcessArgument $_ }) -join " "

  $process = Start-Process `
    -FilePath $pythonExe `
    -ArgumentList $arguments `
    -WorkingDirectory $RepoRoot `
    -NoNewWindow `
    -Wait `
    -PassThru `
    -RedirectStandardOutput $stdoutFile `
    -RedirectStandardError $stderrFile

  foreach ($path in @($stdoutFile, $stderrFile)) {
    if (Test-Path $path) {
      Get-Content $path | Tee-Object -FilePath $logFile -Append | Out-Host
    }
  }
  $code = [int]$process.ExitCode
  Write-Log "[$(Get-Date -Format o)] END $Title (exit=$code)"
  if ($code -ne 0 -and -not $AllowFailure) {
    throw "$Title falhou com exit code $code"
  }
  return [int]$code
}

$dailyArgs = @(
  "scripts/run_b3_daily_job.py",
  "--user-id", "$UserId",
  "--full-universe",
  "--flush-max-retries", "$FlushRetries",
  "--skip-dashboard-seed"
)

$skipBuildArgs = @(
  "scripts/run_b3_daily_job.py",
  "--user-id", "$UserId",
  "--skip-build",
  "--flush-max-retries", "$FlushRetries",
  "--skip-dashboard-seed"
)

$feedRefreshArgs = @(
  "scripts/refresh_market_feeds.py",
  "--user-id", "$UserId",
  "--b3-max-days-per-instrument", "$B3RefreshMaxDaysPerInstrument",
  "--crypto-lookback-hours", "$CryptoLookbackHours"
)

$currentThesesArgs = @(
  "scripts/run_current_thesis_by_front_job.py",
  "--user-id", "$UserId",
  "--recent-bars-window", "$CurrentRecentBarsWindow"
)

$opsGuardArgs = @(
  "scripts/run_grao_ops_guard.py",
  "--user-id", "$UserId",
  "--write-dashboard-seed"
)

$publishArgs = @("scripts/publish_dashboard_seed.py")

if (-not $SkipFeedRefresh) {
  $feedCode = [int](Invoke-Step -Title "refresh_market_feeds" -ArgList $feedRefreshArgs -AllowFailure)
  if ($feedCode -ne 0) {
    Write-Log "[$(Get-Date -Format o)] WARN refresh de feeds falhou parcialmente; ops guard fara o bloqueio se necessario"
  }
} else {
  Write-Log "[$(Get-Date -Format o)] SKIP refresh_market_feeds"
}

$runCode = 0
try {
  $runCode = [int](Invoke-Step -Title "run_b3_daily_job(full)" -ArgList $dailyArgs)
} catch {
  Write-Log "[$(Get-Date -Format o)] WARN tentativa full falhou: $($_.Exception.Message)"
  $runCode = [int](Invoke-Step -Title "run_b3_daily_job(skip-build retry)" -ArgList $skipBuildArgs -AllowFailure)
}

if ($runCode -ne 0) {
  Write-Log "[$(Get-Date -Format o)] ERROR job diario nao concluiu; publish nao executado"
  exit $runCode
}

if (-not $SkipCurrentTheses) {
  $currentCode = [int](Invoke-Step -Title "run_current_thesis_by_front_job" -ArgList $currentThesesArgs)
  if ($currentCode -ne 0) {
    Write-Log "[$(Get-Date -Format o)] ERROR gerador de teses atuais nao concluiu; publish nao executado"
    exit $currentCode
  }
} else {
  Write-Log "[$(Get-Date -Format o)] SKIP run_current_thesis_by_front_job"
}

if (-not $SkipOpsGuard) {
  $guardCode = [int](Invoke-Step -Title "run_grao_ops_guard" -ArgList $opsGuardArgs -AllowFailure)
  if ($guardCode -ne 0) {
    Write-Log "[$(Get-Date -Format o)] WARN ops guard encontrou bloqueios; publicando seed com diagnostico"
  }
} else {
  Write-Log "[$(Get-Date -Format o)] SKIP run_grao_ops_guard"
}

$publishCode = [int](Invoke-Step -Title "publish_dashboard_seed" -ArgList $publishArgs -AllowFailure)
if ($publishCode -ne 0) {
  Write-Log "[$(Get-Date -Format o)] WARN publish falhou (sem bloquear ciclo)"
}

Write-Log "[$(Get-Date -Format o)] DONE ciclo completo"
exit 0
