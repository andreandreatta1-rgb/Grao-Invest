param(
  [string]$RepoRoot = "",
  [int]$UserId = 1,
  [int]$FlushRetries = 160
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
  $RepoRoot = Split-Path -Parent $PSScriptRoot
}
$RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path

function New-GraoPowerShellAction {
  param(
    [string]$ScriptPath,
    [string]$ExtraArguments = ""
  )
  $arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$ScriptPath`" $ExtraArguments".Trim()
  New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument $arguments `
    -WorkingDirectory $RepoRoot
}

$b3Script = Join-Path $RepoRoot "scripts\run_b3_automation_cycle.ps1"
$nightScript = Join-Path $RepoRoot "scripts\run_case_study_overnight_loop.ps1"

$principal = New-ScheduledTaskPrincipal `
  -UserId $env:USERNAME `
  -LogonType Interactive `
  -RunLevel Limited

$settings = New-ScheduledTaskSettingsSet `
  -StartWhenAvailable `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -MultipleInstances IgnoreNew

$tasks = @(
  @{ Name = "GraoInvest-B3-01"; At = "00:30"; Script = $b3Script; Args = "-RepoRoot `"$RepoRoot`" -UserId $UserId -FlushRetries $FlushRetries" },
  @{ Name = "GraoInvest-B3-02"; At = "04:30"; Script = $b3Script; Args = "-RepoRoot `"$RepoRoot`" -UserId $UserId -FlushRetries $FlushRetries" },
  @{ Name = "GraoInvest-B3-03"; At = "08:30"; Script = $b3Script; Args = "-RepoRoot `"$RepoRoot`" -UserId $UserId -FlushRetries $FlushRetries" },
  @{ Name = "GraoInvest-B3-04"; At = "12:30"; Script = $b3Script; Args = "-RepoRoot `"$RepoRoot`" -UserId $UserId -FlushRetries $FlushRetries" },
  @{ Name = "GraoInvest-B3-05"; At = "16:30"; Script = $b3Script; Args = "-RepoRoot `"$RepoRoot`" -UserId $UserId -FlushRetries $FlushRetries" },
  @{ Name = "GraoInvest-CaseStudy-Night"; At = "22:00"; Script = $nightScript; Args = "-SleepSeconds 5 -PublishEveryMinutes 30 -EndHour 6" }
)

$installed = @()
foreach ($task in $tasks) {
  $action = New-GraoPowerShellAction -ScriptPath $task.Script -ExtraArguments $task.Args
  $trigger = New-ScheduledTaskTrigger -Daily -At ([datetime]::ParseExact($task.At, "HH:mm", $null))
  Register-ScheduledTask `
    -TaskName $task.Name `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Force | Out-Null
  $installed += $task.Name
}

[pscustomobject]@{
  status = "installed"
  repo_root = $RepoRoot
  tasks = $installed
} | ConvertTo-Json -Depth 4
