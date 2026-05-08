param(
    [string]$FrontendDir = "apps/thesis-lab-view",
    [string]$TargetDir = "services/api/frontend_dist"
)

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$sourceDir = Join-Path $repoRoot $FrontendDir
$distDir = Join-Path $sourceDir "dist"
$targetPath = Join-Path $repoRoot $TargetDir

if (-not (Test-Path $distDir)) {
    throw "Frontend dist not found at $distDir. Run the thesis-lab-view build first."
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
