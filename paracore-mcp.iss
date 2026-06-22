; ═══════════════════════════════════════════════════════════════════════════════
; Paracore Generalist MCP Installer
; ═══════════════════════════════════════════════════════════════════════════════
;
; Usage:
;   ISCC -DMCPName=mcp -DMCPTitle="Paracore-MCP" -DVersion=4.6.0 paracore-mcp.iss
;
; Output: Paracore-MCP-v4.6.0.exe
; ═══════════════════════════════════════════════════════════════════════════════

#ifndef MCPName
  #define MCPName "mcp"
#endif
#ifndef MCPTitle
  #define MCPTitle "Paracore-MCP"
#endif
#ifndef Version
  #define Version "0.0.0"
#endif

#define ExeName "paracore-" + MCPName
#define OutputBase MCPTitle + "-v" + Version

[Setup]
AppId={{Paracore-F9E8D7C6-B5A4-3210-FEDC-BA9876543210}}
AppName={#MCPTitle}
AppVersion={#Version}
AppPublisher=Paracore
AppPublisherURL=https://paracore.io
AppSupportURL=https://paracore.io/support
VersionInfoVersion={#Version}

OutputBaseFilename={#OutputBase}

Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

; Per-user install under %APPDATA% — Claude Desktop looks here for MCP servers
DefaultDirName={userappdata}\paracore-data\mcp-servers
DisableDirPage=yes

SetupIconFile="{#IconPath}"
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
UninstallDisplayName={#MCPTitle} (Paracore MCP Server)
UninstallDisplayIcon={app}\{#ExeName}.exe

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; The MCP executable — built by build-mcp.ps1 via PyInstaller
Source: "dist\{#ExeName}.exe"; DestDir: "{app}"; Flags: ignoreversion

; Reference docs — bundled as MCP resources
Source: "REPL_GUIDE.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "EXTENSION_METHODS.md"; DestDir: "{app}"; Flags: ignoreversion

[Run]
Filename: "{cmd}"; Parameters: "/c echo {#MCPTitle} v{#Version} installed successfully. && echo Location: {app}"; \
    Flags: nowait skipifsilent runhidden; \
    Description: "Confirm installation"

[UninstallDelete]
Type: files; Name: "{app}\paracore_mcp.log"
