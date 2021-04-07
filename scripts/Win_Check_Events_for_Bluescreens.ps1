# This will check for Bluescreen events on your system

$ErrorActionPreference= 'silentlycontinue'
$TimeSpan = (Get-Date) - (New-TimeSpan -Day 1)

if (Get-WinEvent -FilterHashtable @{LogName='application';ID='1001';ProviderName='Windows Error Reporting';Level=4;Data='BlueScreen';StartTime=$TimeSpan})

{
Write-Output "There has been bluescreen events detected on your system"
Get-WinEvent -FilterHashtable @{LogName='application';ID='1001';ProviderName='Windows Error Reporting';Level=4;Data='BlueScreen';StartTime=$TimeSpan}
exit 1
}

{
else 
Write-Output "No bluescreen events detected in the past 24 hours."
exit 0
}

Exit $LASTEXITCODE
