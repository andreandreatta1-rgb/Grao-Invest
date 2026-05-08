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

& (Join-Path $PSScriptRoot "install_grao_tasks.ps1") `
  -RepoRoot $RepoRoot `
  -UserId $UserId `
  -FlushRetries $FlushRetries

& (Join-Path $PSScriptRoot "verify_grao_tasks.ps1") `
  -RepoRoot $RepoRoot `
  -UserId $UserId
