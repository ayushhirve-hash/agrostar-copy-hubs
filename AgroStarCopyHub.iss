[Setup]
AppName=AgroStar Copy Hub
AppVersion=1.0.0
DefaultDirName={autopf}\AgroStar Copy Hub
DefaultGroupName=AgroStar Copy Hub
OutputDir=dist
OutputBaseFilename=AgroStar Copy Hub Setup
Compression=lzma
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
DisableProgramGroupPage=yes

[Files]
Source: "dist\AgroStar Copy Hub.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\AgroStar Copy Hub"; Filename: "{app}\AgroStar Copy Hub.exe"
Name: "{autodesktop}\AgroStar Copy Hub"; Filename: "{app}\AgroStar Copy Hub.exe"

[Run]
Filename: "{app}\AgroStar Copy Hub.exe"; Description: "Launch AgroStar Copy Hub"; Flags: nowait postinstall skipifsilent
