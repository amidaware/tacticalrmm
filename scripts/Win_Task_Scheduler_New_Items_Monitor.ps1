<#
.Synopsis
    Event Viewer - Task Scheduler New Item Notification
.DESCRIPTION
    Event Viewer Monitor - Notify when new Task Scheduler item is created
.EXAMPLE
    365
.NOTES
    v1 dinger initial release
    v1.1 silversword adding command parameters 11/2021    
#>


$ErrorActionPreference = 'silentlycontinue'
if ($Args.Count -eq 0) {
    $TimeSpan = (Get-Date) - (New-TimeSpan -Day 1)
}
else {
    $TimeSpan = (Get-Date) - (New-TimeSpan -Day $param1)
}

if (Get-WinEvent -FilterHashtable @{LogName = 'Microsoft-Windows-TaskScheduler/Operational'; ID = '106'; StartTime = $TimeSpan } | Where-Object -Property Message -notlike *$env:COMPUTERNAME*) {
    Write-Output "New Task Has Been Added"
    Get-WinEvent -FilterHashtable @{LogName = 'Microsoft-Windows-TaskScheduler/Operational'; ID = '106'; StartTime = $TimeSpan }
    Get-WinEvent -FilterHashtable @{LogName = 'Microsoft-Windows-TaskScheduler/Operational'; ID = '141'; StartTime = $TimeSpan }
    exit 1
}

else {
    Write-Output "No changes with Task Scheduler"
    exit 0
}


Exit $LASTEXITCODE