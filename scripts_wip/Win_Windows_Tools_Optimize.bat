rem https://github.com/jebofponderworthy/windows-tools
@echo off

echo --------------------------------------------
echo Download and Run All Optimize Script Applets
echo --------------------------------------------

echo:
echo Verifying appropriate Powershell is present ...
echo ---
@"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -Command "[string]$PSVersionTable.PSVersion.Major + '.' + [string]$PSVersionTable.PSVersion.Minor" > psversion.txt
<psversion.txt set /p psversion=
@del psversion.txt
echo Powershell version is: %psversion%
If %psversion% LSS "5.1" (
	Powershell version is less than 5.1, cannot continue.
	pause
	Exit
)
echo Ready to go.

echo:
echo Preparing...
echo ---
echo:
@"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -InputFormat None -ExecutionPolicy Bypass -Command ^
"$wco = (New-Object System.Net.WebClient); $wco.DownloadFile('https://raw.githubusercontent.com/jebofponderworthy/windows-tools/master/tools/Optimize.ps1','Optimize.ps1')"

echo:
echo Initiating...
echo ---
echo:
@"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoProfile -InputFormat None -ExecutionPolicy Bypass -Command ".\Optimize.ps1"

@del Optimize.ps1

