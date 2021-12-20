rem If you want to deploy TRMM agent using AD, intune, mesh, teamviewer, Group Policy GPO etc this is a sample CMD script for deploying tactical

if not exist C:\TEMP\TRMM md C:\TEMP\TRMM
powershell Set-ExecutionPolicy -ExecutionPolicy Unrestricted
powershell Add-MpPreference -ExclusionPath C:\TEMP\TRMM
powershell Add-MpPreference -ExclusionPath "C:\Program Files\TacticalAgent\*"
powershell Add-MpPreference -ExclusionPath C:\Windows\Temp\winagent-v*.exe
powershell Add-MpPreference -ExclusionPath "C:\Program Files\Mesh Agent\*"
powershell Add-MpPreference -ExclusionPath C:\Windows\Temp\TRMM\*
cd c:\temp\trmm
powershell Invoke-WebRequest "deployment url" -Outfile tactical.exe
"C:\Program Files\TacticalAgent\unins000.exe" /VERYSILENT
start tactical.exe
powershell Remove-MpPreference -ExclusionPath C:\TEMP\TRMM