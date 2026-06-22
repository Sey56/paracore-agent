# Set-Version.ps1
# Propagates the version from the root VERSION file to all relevant files.

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$RootDir = Split-Path -Parent $ScriptRoot

$VersionPath = Join-Path $RootDir "VERSION"
if (-not (Test-Path $VersionPath)) {
    Write-Error "VERSION file not found at $VersionPath"
    exit 1
}

$Version = (Get-Content $VersionPath).Trim()

Write-Host "Updating paracore-agent to version $Version..." -ForegroundColor Cyan

# 1. Update pyproject.toml
$PyprojectPath = Join-Path $RootDir "pyproject.toml"
if (Test-Path $PyprojectPath) {
    $content = Get-Content $PyprojectPath -Raw
    $newContent = $content -replace 'version\s*=\s*"[^"]+"', "version = `"$Version`""
    if ($content -ne $newContent) {
        $newContent | Set-Content $PyprojectPath -NoNewline
        Write-Host "Updated pyproject.toml"
    }
}

# 2. The build-mcp.ps1 reads from VERSION at runtime — no hardcoded version to update.
# 3. The paracore-mcp.iss receives version via -DVersion from build-mcp.ps1.

Write-Host "Version sync complete!" -ForegroundColor Green
