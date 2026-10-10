#ifndef AppVersion
  #define AppVersion "0.3.0"
#endif
#ifndef BundlePath
  #error BundlePath required
#endif
#ifndef OutputPath
  #error OutputPath required
#endif
[Setup]
AppId={{A96D4E08-2E37-4A93-B9B7-0145D6C87453}
AppName=FGTS Guias
AppVersion={#AppVersion}
AppPublisher=FGTS Guias
AppPublisherURL=https://github.com/JoaoLucasDaSilvaOliveira/fgts-guias
DefaultDirName={localappdata}\Programs\FGTS Guias
DefaultGroupName=FGTS Guias
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputPath}
OutputBaseFilename=fgts-guias-v{#AppVersion}-windows-x64-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\..\app\windows\runner\resources\app_icon.ico
UninstallDisplayIcon={app}\fgts_guias.exe
CloseApplications=no
RestartApplications=no
AppMutex=Local\FGTSGuiasRunning
[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; Flags: unchecked
[Files]
Source: "{#BundlePath}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{autoprograms}\FGTS Guias"; Filename: "{app}\fgts_guias.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\FGTS Guias"; Filename: "{app}\fgts_guias.exe"; WorkingDir: "{app}"; Tasks: desktopicon
[Run]
Filename: "{app}\fgts_guias.exe"; Description: "Abrir FGTS Guias"; Flags: nowait postinstall skipifsilent
[Code]
function InitializeSetup(): Boolean;
begin
  Result := FindWindowByWindowName('FGTS Guias') = 0;
  if not Result then
    MsgBox('Feche o FGTS Guias antes de instalar ou atualizar.', mbInformation, MB_OK);
end;
