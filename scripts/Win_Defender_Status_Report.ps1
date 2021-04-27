<#
.Synopsis
   Defender - Status Report
.DESCRIPTION
   This will check Event Log for Windows Defender Malware and Antispyware reports, otherwise will report as Healthy. By default if no command parameter is provided it will check the last 1 day (good for a scheduled daily task). 
   If a number is provided as a command parameter it will search back that number of days back provided (good for collecting all AV alerts on the computer).
.EXAMPLE
   Win_Defender_Status_reports.ps1 365
#>

$param1 = $args[0]

$ErrorActionPreference = 'silentlycontinue'
if ($Args.Count -eq 0) {
    $TimeSpan = (Get-Date) - (New-TimeSpan -Day 1)
}
else {
    $TimeSpan = (Get-Date) - (New-TimeSpan -Day $param1)
}

if (Get-WinEvent -FilterHashtable @{LogName = 'Microsoft-Windows-Windows Defender/Operational'; ID = '1116', '1118', '1015', '1006', '5010', '5012', '5001', '1123'; StartTime = $TimeSpan }) {
    Write-Output "Virus Found or Issue with Defender"
    Get-WinEvent -FilterHashtable @{LogName = 'Microsoft-Windows-Windows Defender/Operational'; ID = '1116', '1118', '1015', '1006', '5010', '5012', '5001', '1123'; StartTime = $TimeSpan }
    exit 1
}


else {
    Write-Output "No Virus Found, Defender is Healthy"
    Get-WinEvent -FilterHashtable @{LogName = 'Microsoft-Windows-Windows Defender/Operational'; ID = '1150', '1001'; StartTime = $TimeSpan }
    exit 0
}


Exit $LASTEXITCODE
