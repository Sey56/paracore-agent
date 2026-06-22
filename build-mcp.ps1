param(
    [switch]$Installer = $false,
    [string]$Version = "4.6.0"
)

$mcpName = "paracore-mcp"
$description = "Paracore-MCP"

Write-Host "--- Building $description ---" -ForegroundColor Cyan
Write-Host "  Output: $mcpName.exe" -ForegroundColor Cyan

$AgentRoot = $PSScriptRoot
$BuildProjectDir = Join-Path $AgentRoot "mcp-build"

# 1. Sync the isolated build environment
Write-Host "Syncing MCP build environment..." -ForegroundColor Yellow
Push-Location $BuildProjectDir
uv sync 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "uv sync failed!" -ForegroundColor Red
    Pop-Location
    exit $LASTEXITCODE
}
$BuildPython = Join-Path $BuildProjectDir ".venv\Scripts\python.exe"
Pop-Location

# 2. Build the executable
Write-Host "Compiling mcp_server.py into standalone executable..." -ForegroundColor Yellow
Push-Location $AgentRoot
& $BuildPython -m PyInstaller --onefile --name $mcpName --paths . `
    --exclude-module logfire `
    --hidden-import mcp `
    --hidden-import mcp.server.fastmcp `
    --hidden-import grpc `
    --hidden-import google.protobuf `
    --hidden-import google.protobuf.descriptor_pool `
    --hidden-import google.protobuf.runtime_version `
    --hidden-import google.protobuf.symbol_database `
    --hidden-import google.protobuf.internal.builder `
    --hidden-import mcp_core `
    --hidden-import mcp_core.prompts `
    --add-data "REPL_GUIDE.md;." `
    --add-data "EXTENSION_METHODS.md;." `
    mcp_server.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed!" -ForegroundColor Red
    Pop-Location
    exit $LASTEXITCODE
}
Pop-Location

# 3. Move to dist/
$DistDir = Join-Path $AgentRoot "dist"
if (!(Test-Path $DistDir)) { New-Item -ItemType Directory -Path $DistDir | Out-Null }

$ExePath = Join-Path $AgentRoot "dist\$mcpName.exe"
$DestPath = Join-Path $DistDir "$mcpName.exe"

Write-Host "Copying executable to dist/..." -ForegroundColor Yellow
Copy-Item -Path $ExePath -Destination $DestPath -Force

Write-Host "--- PyInstaller Build Complete! ---" -ForegroundColor Green
Write-Host "Executable: $DestPath" -ForegroundColor Green

# ── 4. (Optional) Build Windows installer via Inno Setup ─────────────────
if ($Installer) {
    $ISCC = $null
    $candidates = @(
        "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { $ISCC = $c; break }
    }

    if (-not $ISCC) {
        Write-Host "ERROR: Inno Setup 6 not found. Install from https://jrsoftware.org/isinfo.php" -ForegroundColor Red
        exit 1
    }

    Write-Host "Building Windows installer with Inno Setup 6..." -ForegroundColor Yellow
    Write-Host "  Version:  $Version" -ForegroundColor DarkGray

    $InstallersDir = Join-Path $AgentRoot "installers"
    $IssFile = Join-Path $AgentRoot "paracore-mcp.iss"
    if (-not (Test-Path $IssFile)) {
        Write-Host "NOTE: No paracore-mcp.iss found — skipping installer. Copy from paracore-pro if needed." -ForegroundColor Yellow
    }
    else {
        Push-Location $InstallersDir
        & $ISCC -D"MCPName=mcp" -D"MCPTitle=Paracore-MCP" -D"Version=$Version" "-O$InstallersDir" $IssFile
        $issExit = $LASTEXITCODE
        Pop-Location

        if ($issExit -ne 0) {
            Write-Host "Inno Setup build failed!" -ForegroundColor Red
            exit $issExit
        }

        Write-Host "Installer built successfully!" -ForegroundColor Green
    }
}
else {
    Write-Host ""
    Write-Host "To build an installer: add -Installer" -ForegroundColor DarkGray
    Write-Host "  ./build-mcp.ps1 -Installer" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "To install manually: copy $mcpName.exe to" -ForegroundColor Yellow
    Write-Host "  %APPDATA%\paracore-data\mcp-servers\" -ForegroundColor Cyan
    Write-Host "Then add to claude_desktop_config.json:" -ForegroundColor Yellow
    Write-Host "  { ""command"": ""%APPDATA%\\paracore-data\\mcp-servers\\$mcpName.exe"", ""args"": [] }" -ForegroundColor Gray
}
