param(
  [string]$RepoRoot = "",
  [int]$UserId = 1,
  [string]$Instruments = "PETR4,VALE3,ITUB4,BBDC4,BBAS3,ABEV3,WEGE3,B3SA3,RENT3,SUZB3,JBSS3,PRIO3,RADL3,GGBR4,VBBR3,LREN3,HAPV3,BPAC11,RAIL3,CMIG4",
  [int]$HorizonBars = 8,
  [int]$SleepSeconds = 5,
  [int]$EndHour = 6,
  [int]$PublishEveryMinutes = 30,
  [int]$MaxIterations = 0,
  [int]$MaxConsecutiveFailures = 20
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
  $RepoRoot = Split-Path -Parent $PSScriptRoot
}

$logDir = Join-Path $RepoRoot "data\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = Join-Path $logDir ("case_study_overnight_" + $stamp + ".log")

function Write-Log {
  param([string]$Message)
  $line = "[$(Get-Date -Format o)] $Message"
  Add-Content -Path $logFile -Value $line
  Write-Host $line
}

function Invoke-PyStep {
  param(
    [string]$Title,
    [string[]]$ArgList,
    [switch]$AllowFailure
  )
  Write-Log "START $Title"
  Push-Location $RepoRoot
  try {
    $null = (& py -3 @ArgList 2>&1 | Tee-Object -FilePath $logFile -Append)
    $code = $LASTEXITCODE
  } finally {
    Pop-Location
  }
  Write-Log "END $Title (exit=$code)"
  if ($code -ne 0 -and -not $AllowFailure) {
    throw "$Title falhou com exit code $code"
  }
  return [int]$code
}

$instrumentPool = @(
  $Instruments.Split(",") | ForEach-Object { $_.Trim().ToUpperInvariant() } | Where-Object { $_ }
)

$now = Get-Date
$endTime = Get-Date -Hour $EndHour -Minute 0 -Second 0
if ($now -ge $endTime) {
  $endTime = $endTime.AddDays(1)
}

Write-Log "OVERNIGHT LOOP START | end_time=$($endTime.ToString('s')) | user_id=$UserId"

$nextPublish = (Get-Date).AddMinutes([Math]::Max(5, $PublishEveryMinutes))
$total = 0
$ok = 0
$fail = 0
$consecutiveFail = 0

while ((Get-Date) -lt $endTime) {
  if ($MaxIterations -gt 0 -and $total -ge $MaxIterations) {
    Write-Log "MaxIterations atingido ($MaxIterations). Encerrando loop."
    break
  }

  $total += 1
  $instrumentCsv = $Instruments
  if ($instrumentPool.Count -gt 3) {
    $takeCount = [Math]::Min($instrumentPool.Count, (Get-Random -Minimum 4 -Maximum ([Math]::Min(8, $instrumentPool.Count) + 1)))
    $instrumentCsv = (($instrumentPool | Get-Random -Count $takeCount) -join ",")
  }
  $caseArgs = @(
    "scripts/run_case_study.py",
    "--user-id", "$UserId",
    "--horizon-bars", "$HorizonBars",
    "--instruments", "$instrumentCsv"
  )
  $code = Invoke-PyStep -Title ("case_study_iteration_" + $total) -ArgList $caseArgs -AllowFailure
  if ($code -eq 0) {
    $ok += 1
    $consecutiveFail = 0
  } else {
    $fail += 1
    $consecutiveFail += 1
    if ($consecutiveFail -ge $MaxConsecutiveFailures) {
      Write-Log "Falhas consecutivas atingiram limite ($MaxConsecutiveFailures). Encerrando loop."
      break
    }
  }

  if ((Get-Date) -ge $nextPublish) {
    $refreshArgs = @(
      "scripts/run_b3_daily_job.py",
      "--user-id", "$UserId",
      "--skip-build",
      "--skip-load",
      "--skip-case-study"
    )
    $null = Invoke-PyStep -Title "refresh_dashboard_seed" -ArgList $refreshArgs -AllowFailure
    $null = Invoke-PyStep -Title "publish_dashboard_seed" -ArgList @("scripts/publish_dashboard_seed.py") -AllowFailure
    $nextPublish = (Get-Date).AddMinutes([Math]::Max(5, $PublishEveryMinutes))
  }

  Start-Sleep -Seconds ([Math]::Max(1, $SleepSeconds))
}

$refreshArgs = @(
  "scripts/run_b3_daily_job.py",
  "--user-id", "$UserId",
  "--skip-build",
  "--skip-load",
  "--skip-case-study"
)
$null = Invoke-PyStep -Title "final_refresh_dashboard_seed" -ArgList $refreshArgs -AllowFailure
$null = Invoke-PyStep -Title "final_publish_dashboard_seed" -ArgList @("scripts/publish_dashboard_seed.py") -AllowFailure

Write-Log "OVERNIGHT LOOP DONE | total=$total | ok=$ok | fail=$fail"
exit 0
