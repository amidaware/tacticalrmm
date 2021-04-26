# This will check for Malware, Antispyware, that Windows Defender is Healthy, last scan etc within the last 24 hours
# If parameter is supplied, it will search the log for that many days

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
