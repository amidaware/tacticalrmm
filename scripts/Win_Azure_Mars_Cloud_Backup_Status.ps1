$ErrorActionPreference= 'silentlycontinue'
$TimeSpan = (Get-Date) - (New-TimeSpan -Day 1)

##Check for Errors in Backup
if (Get-WinEvent -FilterHashtable @{LogName='CloudBackup/Operational';ID='11','18';StartTime=$TimeSpan}) 

{
Write-Host "Cloud Backup Mars Ended with Errors"
Get-WinEvent -FilterHashtable @{LogName='CloudBackup/Operational';ID='1','14','11','18','16';StartTime=$TimeSpan}
exit 1
}


else 

{
Write-Host "Cloud Backup Mars Backup Is Working Correctly"
Get-WinEvent -FilterHashtable @{LogName='CloudBackup/Operational';ID='1','14','16'}
exit 0
}


Exit $LASTEXITCODE