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

$targetIndexPath = Join-Path $targetPath "index.html"
$targetIndexHtml = Get-Content -Raw -LiteralPath $targetIndexPath
$entryAssetMatch = [regex]::Match($targetIndexHtml, 'src="/(?<asset>assets/index-[^"]+\.js)"')
if (-not $entryAssetMatch.Success) {
    throw "Synced frontend index.html does not point to an assets/index-*.js bundle."
}

$gitCommit = (& git -C $repoRoot rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or -not $gitCommit) {
    throw "Could not resolve git commit for frontend build-info."
}
$gitCommitShort = (& git -C $repoRoot rev-parse --short=12 HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or -not $gitCommitShort) {
    throw "Could not resolve short git commit for frontend build-info."
}

$buildInfo = [ordered]@{
    ui_revision = "UI rev soul-4"
    source_app = $FrontendDir.Replace("\", "/")
    git_commit = $gitCommit
    git_commit_short = $gitCommitShort
    built_at = (Get-Date).ToUniversalTime().ToString("o")
    entry_asset = $entryAssetMatch.Groups["asset"].Value
    required_markers = $requiredMarkers
}
$buildInfoPath = Join-Path $targetPath "build-info.json"
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($buildInfoPath, ($buildInfo | ConvertTo-Json -Depth 4), $utf8NoBom)

Write-Host "Synced frontend bundle from $distDir to $targetPath"
