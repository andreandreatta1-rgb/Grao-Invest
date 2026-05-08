param(
  [string]$RepoRoot = "",
  [int]$UserId = 1
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
  $RepoRoot = Split-Path -Parent $PSScriptRoot
}
$RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path

$expected = @(
  @{ Name = "GraoInvest-B3-01"; Script = Join-Path $RepoRoot "scripts\run_b3_automation_cycle.ps1"; Required = @("-RepoRoot", $RepoRoot, "-UserId", "$UserId") },
  @{ Name = "GraoInvest-B3-02"; Script = Join-Path $RepoRoot "scripts\run_b3_automation_cycle.ps1"; Required = @("-RepoRoot", $RepoRoot, "-UserId", "$UserId") },
  @{ Name = "GraoInvest-B3-03"; Script = Join-Path $RepoRoot "scripts\run_b3_automation_cycle.ps1"; Required = @("-RepoRoot", $RepoRoot, "-UserId", "$UserId") },
  @{ Name = "GraoInvest-B3-04"; Script = Join-Path $RepoRoot "scripts\run_b3_automation_cycle.ps1"; Required = @("-RepoRoot", $RepoRoot, "-UserId", "$UserId") },
  @{ Name = "GraoInvest-B3-05"; Script = Join-Path $RepoRoot "scripts\run_b3_automation_cycle.ps1"; Required = @("-RepoRoot", $RepoRoot, "-UserId", "$UserId") },
  @{ Name = "GraoInvest-CaseStudy-Night"; Script = Join-Path $RepoRoot "scripts\run_case_study_overnight_loop.ps1"; Required = @("-SleepSeconds", "5", "-PublishEveryMinutes", "30", "-EndHour", "6") }
)

$results = @()
$ok = $true

foreach ($item in $expected) {
  $issues = @()
  $task = Get-ScheduledTask -TaskName $item.Name -ErrorAction SilentlyContinue
  $info = $null
  $action = $null
  if ($null -eq $task) {
    $issues += "task_missing"
  } else {
    $action = $task.Actions | Select-Object -First 1
    $info = Get-ScheduledTaskInfo -TaskName $item.Name -ErrorAction SilentlyContinue
    if ($action.Execute -ne "powershell.exe") {
      $issues += "execute_not_powershell"
    }
    if ([string]::IsNullOrWhiteSpace($action.WorkingDirectory) -or $action.WorkingDirectory -ne $RepoRoot) {
      $issues += "working_directory_mismatch"
    }
    if ($action.Arguments -notlike "*$($item.Script)*") {
      $issues += "script_path_missing_or_unquoted"
    }
    foreach ($required in $item.Required) {
      if ($action.Arguments -notlike "*$required*") {
        $issues += "argument_missing:$required"
      }
    }
    if ($action.Execute -like "$env:USERPROFILE\OneDrive*") {
      $issues += "execute_path_truncated_by_spaces"
    }
  }

  if ($issues.Count -gt 0) {
    $ok = $false
  }
  $results += [pscustomobject]@{
    task_name = $item.Name
    ok = ($issues.Count -eq 0)
    issues = $issues
    execute = if ($action) { $action.Execute } else { "" }
    arguments = if ($action) { $action.Arguments } else { "" }
    working_directory = if ($action) { $action.WorkingDirectory } else { "" }
    last_run_time = if ($info) { $info.LastRunTime } else { $null }
    last_task_result = if ($info) { $info.LastTaskResult } else { $null }
    next_run_time = if ($info) { $info.NextRunTime } else { $null }
  }
}

$payload = [pscustomobject]@{
  status = if ($ok) { "ok" } else { "fail" }
  repo_root = $RepoRoot
  checked_at = (Get-Date).ToUniversalTime().ToString("o")
  tasks = $results
}

$payload | ConvertTo-Json -Depth 6
if (-not $ok) {
  exit 1
}
