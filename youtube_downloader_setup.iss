; YouTube Downloader Inno Setup Script
; Version 1.2
;
; IMPORTANT: Before compiling this installer, make sure you have:
; 1. Built the exe with PyInstaller
; 2. Created bin folder at: dist\youtube_downloader\bin\
; 3. Copied ffmpeg.exe to: dist\youtube_downloader\bin\ffmpeg.exe
; 4. (Optional) Copied yt-dlp.exe to: dist\youtube_downloader\bin\yt-dlp.exe

#define MyAppName "YouTube Downloader"
#define MyAppVersion "1.2"
#define MyAppPublisher "Sujit"
#define MyAppURL "https://github.com/SSujitX"
#define MyAppExeName "youtube_downloader.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
AppId={{A8B9C1D2-E3F4-5678-9ABC-DEF012345678}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=.\
OutputBaseFilename=YouTubeDownloader_v{#MyAppVersion}_Setup
SetupIconFile=yt.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Copy all files from dist\youtube_downloader including bin folder
Source: "dist\youtube_downloader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up any files created by the app during runtime
Type: filesandordirs; Name: "{app}\bin\*.tmp"
