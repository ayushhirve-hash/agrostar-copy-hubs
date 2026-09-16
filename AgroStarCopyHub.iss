[Setup]
AppName=AgroStar Copy Hub
AppVersion=1.2.0
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\AgroStar Copy Hub
DefaultGroupName=AgroStar Copy Hub
OutputDir=dist
OutputBaseFilename=AgroStar Copy Hub Setup
Compression=lzma
SolidCompression=yes
DisableProgramGroupPage=yes

[Files]
Source: "dist\AgroStar Copy Hub.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{userprograms}\AgroStar Copy Hub"; Filename: "{app}\AgroStar Copy Hub.exe"
Name: "{userdesktop}\AgroStar Copy Hub"; Filename: "{app}\AgroStar Copy Hub.exe"
Name: "{userstartup}\AgroStar Copy Hub"; Filename: "{app}\AgroStar Copy Hub.exe"; Parameters: "--background"

[Run]
Filename: "{app}\AgroStar Copy Hub.exe"; Description: "Launch AgroStar Copy Hub"; Flags: nowait postinstall skipifsilent
