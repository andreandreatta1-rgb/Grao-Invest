param(
    [string]$FrontendDir = "apps/grao-invest-cockpit",
    [string]$TargetDir = "services/api/frontend_dist"
)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$sourceDir = Join-Path $repoRoot $FrontendDir
$distDir = Join-Path $sourceDir "dist"
$targetPath = Join-Path $repoRoot $TargetDir

if (-not (Test-Path $distDir)) {
    throw "Frontend dist not found at $distDir. Run the grao-invest-cockpit build first."
}

$indexPath = Join-Path $distDir "index.html"
if (-not (Test-Path $indexPath)) {
    throw "Frontend index.html not found at $indexPath."
}

$bundleFiles = Get-ChildItem -Path (Join-Path $distDir "assets") -Filter "*.js" -File -ErrorAction SilentlyContinue
if (-not $bundleFiles) {
    throw "Frontend JS bundle not found under $(Join-Path $distDir "assets")."
}

$bundleText = ($bundleFiles | ForEach-Object { Get-Content -Raw -LiteralPath $_.FullName }) -join "`n"
$requiredMarkers = @(
    "UI rev soul-4",
    "A Grande Obra",
    "Evolução do método",
    "Partitura completa",
    "real-estate-score-hero"
)

$missingMarkers = @($requiredMarkers | Where-Object { $bundleText -notlike "*$_*" })
if ($missingMarkers.Count -gt 0) {
    throw "Refusing to sync frontend bundle from $distDir. Missing soul cockpit markers: $($missingMarkers -join ', '). Build apps/grao-invest-cockpit before syncing."
}

Remove-Item -LiteralPath $targetPath -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path $targetPath | Out-Null
Copy-Item -Path (Join-Path $distDir "*") -Destination $targetPath -Recurse -Force

$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

& $python (Join-Path $repoRoot "scripts\apply_frontend_shell_patches.py") --frontend-dist $targetPath
if ($LASTEXITCODE -ne 0) {
    throw "Failed to apply frontend shell patches."
}

Write-Host "Synced frontend bundle from $distDir to $targetPath"
