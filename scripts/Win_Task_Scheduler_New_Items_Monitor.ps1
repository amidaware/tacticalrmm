$ErrorActionPreference= 'silentlycontinue'
$TimeSpan = (Get-Date) - (New-TimeSpan -Day 1)
if (Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-TaskScheduler/Operational';ID='106';StartTime=$TimeSpan} | Where-Object -Property Message -notlike *$env:COMPUTERNAME*)
{
Write-Output "New Task Has Been Added"
Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-TaskScheduler/Operational';ID='106';StartTime=$TimeSpan}
Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-TaskScheduler/Operational';ID='141';StartTime=$TimeSpan}
exit 1
}

else
{
Write-Output "No changes with Task Scheduler"
exit 0
}


Exit $LASTEXITCODE