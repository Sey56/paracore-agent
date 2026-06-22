param(
    [switch]$Installer = $false,
    [string]$Version = ""
)

# Read version from VERSION file if not explicitly provided
if (-not $Version) {
    $VersionFile = Join-Path $PSScriptRoot "VERSION"
    if (Test-Path $VersionFile) {
        $Version = (Get-Content $VersionFile).Trim()
    } else {
        Write-Host "ERROR: VERSION file not found and no -Version specified." -ForegroundColor Red
        exit 1
    }
}

$mcpName = "paracore-mcp"
$description = "Paracore-MCP"

# ── Banner ────────────────────────────────────────────────────────────────
Write-Host '=================================' -ForegroundColor Cyan
Write-Host "  Building $description v$Version"
Write-Host '=================================' -ForegroundColor Cyan

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

# 2. Generate Windows version info file
$vParts = $Version -split '\.'
$vMajor, $vMinor, $vPatch = [int]$vParts[0], [int]$vParts[1], [int]$vParts[2]
$VersionFile = Join-Path $AgentRoot "version-info.txt"
@"
# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=($vMajor, $vMinor, $vPatch, 0),
    prodvers=($vMajor, $vMinor, $vPatch, 0),
    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0,0)
  ),
  kids=[
    StringFileInfo([
      StringTable(u'040904B0', [
        StringStruct(u'CompanyName', u'Paracore'),
        StringStruct(u'FileDescription', u'Paracore MCP Server'),
        StringStruct(u'FileVersion', u'$Version'),
        StringStruct(u'InternalName', u'$mcpName'),
        StringStruct(u'LegalCopyright', u'MIT License'),
        StringStruct(u'OriginalFilename', u'$mcpName.exe'),
        StringStruct(u'ProductName', u'Paracore MCP'),
        StringStruct(u'ProductVersion', u'$Version')
      ])
    ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"@ | Set-Content $VersionFile -Encoding UTF8
Write-Host "  Version info: $Version" -ForegroundColor DarkGray

# 3. Build the executable
Write-Host "Compiling mcp_server.py into standalone executable..." -ForegroundColor Yellow
$IconFile = Join-Path $AgentRoot "icons\$mcpName.ico"
Push-Location $AgentRoot
& $BuildPython -m PyInstaller --onefile --name $mcpName --paths . `
    --version-file $VersionFile `
    --icon $IconFile `
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

# 4. PyInstaller outputs to dist/ directly (we're running from $AgentRoot)
$ExePath = Join-Path $AgentRoot "dist\$mcpName.exe"

Write-Host ''
Write-Host '=================================' -ForegroundColor Green
Write-Host "  $description v$Version — Build Complete"
Write-Host '=================================' -ForegroundColor Green
Write-Host "  Exe: $ExePath"

# ── 5. (Optional) Build Windows installer via Inno Setup ─────────────────
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
    if (!(Test-Path $InstallersDir)) { New-Item -ItemType Directory -Path $InstallersDir | Out-Null }
    $IssFile = Join-Path $AgentRoot "paracore-mcp.iss"
    if (-not (Test-Path $IssFile)) {
        Write-Host "ERROR: paracore-mcp.iss not found at $IssFile" -ForegroundColor Red
        exit 1
    }
    else {
        # Run ISCC from repo root (like free addin build does)
        Push-Location $AgentRoot
        & $ISCC "/dMCPName=mcp" "/dMCPTitle=Paracore-MCP" "/dVersion=$Version" "/dIconPath=$IconFile" "/O$InstallersDir" $IssFile
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
