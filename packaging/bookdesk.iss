; Inno Setup: baut aus der PyInstaller-Ausgabe einen Windows-Installer.
;
; Aufruf (der Workflow macht das selbst):
;   iscc /DVersion=0.1.0 packaging\bookdesk.iss
;
; Bewusst eine Installation ohne Administratorrechte: sie landet unter
; %LOCALAPPDATA%. Das erspart die Nachfrage der Benutzerkontensteuerung,
; die bei einer unsignierten Datei ohnehin nach dem Herausgeber fragt und
; "Unbekannt" anzeigt.

#ifndef Version
  #define Version "0.0.0"
#endif

#define AppName "BookDesk"
#define AppPublisher "BookDesk"
#define AppURL "https://github.com/aaaaaprvdgrwwelt/bookdesk"

[Setup]
AppId={{3F7A9D28-6C51-4E93-8A2F-1D5B7C9E4A02}
AppName={#AppName}
AppVersion={#Version}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist
OutputBaseFilename=BookDesk-{#Version}-Windows-Setup
SetupIconFile=bookdesk.ico
UninstallDisplayIcon={app}\BookDesk.exe
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "deutsch"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; \
  GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\BookDesk\*"; DestDir: "{app}"; \
  Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\BookDesk.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\BookDesk.exe"; \
  Tasks: desktopicon

[Run]
Filename: "{app}\BookDesk.exe"; \
  Description: "{cm:LaunchProgram,{#AppName}}"; \
  Flags: nowait postinstall skipifsilent
