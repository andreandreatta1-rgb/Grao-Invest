param(
  [string]$BaseUrl = "https://grao-invest.vercel.app",
  [string]$OutputDir = "data/reports/visual-smoke",
  [int]$MaxScreens = 0,
  [switch]$StrictMobile
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$BundledNode = "C:\Users\Andreatta\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
$BundledNodeModules = "C:\Users\Andreatta\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules"

if (Test-Path $BundledNode) {
  $Node = $BundledNode
} else {
  $Node = "node"
}

if (Test-Path (Join-Path $BundledNodeModules "playwright")) {
  $env:NODE_PATH = $BundledNodeModules
}

$env:VISUAL_SMOKE_BASE_URL = $BaseUrl
$env:VISUAL_SMOKE_OUTPUT_DIR = $OutputDir
if ($MaxScreens -gt 0) {
  $env:VISUAL_SMOKE_MAX_SCREENS = "$MaxScreens"
} else {
  Remove-Item Env:\VISUAL_SMOKE_MAX_SCREENS -ErrorAction SilentlyContinue
}

if ($StrictMobile) {
  $env:VISUAL_SMOKE_STRICT_MOBILE = "1"
} else {
  Remove-Item Env:\VISUAL_SMOKE_STRICT_MOBILE -ErrorAction SilentlyContinue
}

Push-Location $RepoRoot
try {
  & $Node "scripts\run_visual_smoke.mjs"
  if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
  }
} finally {
  Pop-Location
}
