<#
Creates a powershell script that runs at logon of any user on the machine in the security context of the user.
Useful to set HKCU registry items
Log is written to C:\Users\Public\UserLogonLog.txt
#>

New-Item -ItemType Directory -Force -Path "$ENV:WINDIR\TRMM"
$logonfile = "$ENV:WINDIR\TRMM\logonscript.ps1"
$logfile = "C:\Users\Public\UserLogonLog.txt"

# === LogonScript  ===
$logonscript=@'
Start-Transcript -Path $logfile

# Example: Disable Automatically Hide Scrollbars
# $registryPath = "HKCU:\Control Panel\Accessibility"
# $Name = "DynamicScrollbars"
# $value = "0"
# New-ItemProperty -Path $registryPath -Name $name -Value $value -PropertyType DWORD -Force | Out-Null

Stop-Transcript
'@

$logonscript | Out-File $logonfile

# === Create a link in all users startup folder  ===
 
$Shell = New-Object -ComObject ("WScript.Shell")
$ShortCut = $Shell.CreateShortcut($env:PROGRAMDATA + "\Microsoft\Windows\Start Menu\Programs\StartUp\UserLogon.lnk")
$ShortCut.TargetPath="%systemroot%\System32\WindowsPowerShell\v1.0\powershell.exe"
$ShortCut.Arguments="-executionpolicy bypass -WindowStyle Hidden -file $logonfile"
$ShortCut.WorkingDirectory = "$ENV:WINDIR\TRMM";
$ShortCut.Save() 
