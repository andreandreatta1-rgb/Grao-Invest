param(
  [string]$RepoRoot = "",
  [int]$UserId = 1,
  [int]$FlushRetries = 180,
  [string]$PublicBaseUrl = "https://grao-invest.vercel.app",
  [int]$DeployTimeoutSeconds = 900,
  [switch]$SkipDailyJob,
  [switch]$SkipFrontendBuild,
  [switch]$SkipDeployWait,
  [switch]$SkipVisualSmoke
)

$ErrorActionPreference = "Stop"

function Resolve-GraoRepoRoot {
  param([string]$Candidate)
  if (-not [string]::IsNullOrWhiteSpace($Candidate)) {
    return (Resolve-Path $Candidate).Path
  }
  return (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
}

function Invoke-GraoStep {
  param(
    [string]$Name,
    [scriptblock]$Action
  )

  $startedAt = (Get-Date).ToUniversalTime()
  Write-Host ""
  Write-Host ("==> " + $Name)
  $stepOutput = & $Action 2>&1
  foreach ($line in $stepOutput) {
    Write-Host $line
  }
  $endedAt = (Get-Date).ToUniversalTime()
  return [ordered]@{
    name = $Name
    status = "ok"
    started_at = $startedAt.ToString("o")
    ended_at = $endedAt.ToString("o")
    duration_seconds = [math]::Round(($endedAt - $startedAt).TotalSeconds, 2)
  }
}

function Invoke-PowerShellScript {
  param(
    [string]$ScriptPath,
    [string[]]$Arguments = @()
  )

  $output = & powershell -NoProfile -ExecutionPolicy Bypass -File $ScriptPath @Arguments 2>&1
  foreach ($line in $output) {
    Write-Host $line
  }
  $exitCode = $LASTEXITCODE
  if ($exitCode -ne 0) {
    throw "$ScriptPath failed with exit code $exitCode"
  }
}

function Invoke-FrontendBuild {
  param([string]$FrontendDir)

  $node = "node"
  $npmCli = "C:\Users\Andreatta\.cache\codex-tools\npm-11.6.2\package\bin\npm-cli.js"

  Push-Location $FrontendDir
  try {
    if (Test-Path $npmCli) {
      & $node $npmCli run build
    } else {
      & npm run build
    }
    if ($LASTEXITCODE -ne 0) {
      throw "Frontend build failed with exit code $LASTEXITCODE"
    }
  } finally {
    Pop-Location
  }
}

function Wait-FrontendDeploy {
  param(
    [string]$BaseUrl,
    [string]$ExpectedCommit,
    [int]$TimeoutSeconds
  )

  $versionUrl = $BaseUrl.TrimEnd("/") + "/api/frontend/version"
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  $expectedShort = if ($ExpectedCommit.Length -gt 12) { $ExpectedCommit.Substring(0, 12) } else { $ExpectedCommit }
  $lastPayload = $null

  Write-Host "Waiting for frontend deploy at $versionUrl"
  while ((Get-Date) -lt $deadline) {
    try {
      $payload = Invoke-RestMethod -Uri $versionUrl -Method Get -TimeoutSec 20
      $lastPayload = $payload | ConvertTo-Json -Depth 8
      $commit = [string]($payload.git_commit)
      $short = [string]($payload.git_commit_short)
      $deployedCommit = [string]($payload.deployed_git_commit)
      $deployedShort = [string]($payload.deployed_git_commit_short)

      if (
        $commit -eq $ExpectedCommit `
          -or $short -eq $expectedShort `
          -or $commit.StartsWith($expectedShort) `
          -or $deployedCommit -eq $ExpectedCommit `
          -or $deployedShort -eq $expectedShort `
          -or $deployedCommit.StartsWith($expectedShort)
      ) {
        Write-Host "Deploy confirmed for commit $expectedShort"
        return [ordered]@{
          version_url = $versionUrl
          expected_commit = $ExpectedCommit
          observed_commit = $commit
          observed_commit_short = $short
          deployed_commit = $deployedCommit
          deployed_commit_short = $deployedShort
        }
      }
    } catch {
      $lastPayload = $_.Exception.Message
    }
    Start-Sleep -Seconds 15
  }

  throw "Frontend deploy did not expose commit $expectedShort before timeout. Last response: $lastPayload"
}

$RepoRoot = Resolve-GraoRepoRoot -Candidate $RepoRoot
$scriptsDir = Join-Path $RepoRoot "scripts"
$frontendDir = Join-Path $RepoRoot "apps\grao-invest-cockpit"
$reportDir = Join-Path $RepoRoot "data\reports\daily-e2e"
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
New-Item -ItemType Directory -Force -Path $reportDir | Out-Null

$steps = New-Object System.Collections.Generic.List[object]
$deployInfo = $null

Push-Location $RepoRoot
try {
  $gitCommit = (& git rev-parse HEAD).Trim()
  if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($gitCommit)) {
    throw "Could not resolve local git commit."
  }

  if ($SkipDailyJob) {
    Write-Host "SKIP daily B3 automation cycle"
  } else {
    $steps.Add((Invoke-GraoStep -Name "daily_job" -Action {
      Invoke-PowerShellScript `
        -ScriptPath (Join-Path $scriptsDir "run_b3_automation_cycle.ps1") `
        -Arguments @("-RepoRoot", $RepoRoot, "-UserId", "$UserId", "-FlushRetries", "$FlushRetries")
    }))
  }

  if ($SkipFrontendBuild) {
    Write-Host "SKIP frontend build and sync"
  } else {
    $steps.Add((Invoke-GraoStep -Name "frontend_build" -Action {
      Invoke-FrontendBuild -FrontendDir $frontendDir
    }))
    $steps.Add((Invoke-GraoStep -Name "frontend_sync" -Action {
      Invoke-PowerShellScript -ScriptPath (Join-Path $scriptsDir "sync_thesis_lab_frontend.ps1")
    }))
  }

  $steps.Add((Invoke-GraoStep -Name "quality_gate_local" -Action {
    Invoke-PowerShellScript -ScriptPath (Join-Path $scriptsDir "run_quality_gate.ps1") -Arguments @("-SkipNetwork")
  }))

  if ($SkipDeployWait) {
    Write-Host "SKIP deploy wait"
  } else {
    $steps.Add((Invoke-GraoStep -Name "deploy_wait" -Action {
      $script:deployInfo = Wait-FrontendDeploy `
        -BaseUrl $PublicBaseUrl `
        -ExpectedCommit $gitCommit `
        -TimeoutSeconds $DeployTimeoutSeconds
    }))
  }

  $steps.Add((Invoke-GraoStep -Name "quality_gate_public" -Action {
    Invoke-PowerShellScript `
      -ScriptPath (Join-Path $scriptsDir "run_quality_gate.ps1") `
      -Arguments @(
        "-DashboardUrl",
        ($PublicBaseUrl.TrimEnd("/") + "/api/dashboard/summary/1"),
        "-TimeoutSeconds",
        "90"
      )
  }))

  if ($SkipVisualSmoke) {
    Write-Host "SKIP visual smoke"
  } else {
    $steps.Add((Invoke-GraoStep -Name "visual_smoke_public" -Action {
      Invoke-PowerShellScript `
        -ScriptPath (Join-Path $scriptsDir "run_visual_smoke.ps1") `
        -Arguments @("-BaseUrl", $PublicBaseUrl.TrimEnd("/"), "-StrictMobile")
    }))
  }

  $summary = [ordered]@{
    status = "ok"
    user_id = $UserId
    public_base_url = $PublicBaseUrl
    git_commit = $gitCommit
    deploy = $deployInfo
    steps = $steps
    finished_at = (Get-Date).ToUniversalTime().ToString("o")
  }

  $summaryPath = Join-Path $reportDir ("daily-e2e_" + $stamp + ".json")
  $latestPath = Join-Path $reportDir "latest.json"
  $json = $summary | ConvertTo-Json -Depth 8
  $utf8NoBom = New-Object System.Text.UTF8Encoding $false
  [System.IO.File]::WriteAllText($summaryPath, $json, $utf8NoBom)
  [System.IO.File]::WriteAllText($latestPath, $json, $utf8NoBom)
  Write-Host ""
  Write-Host "Daily E2E completed: $latestPath"
} finally {
  Pop-Location
}
