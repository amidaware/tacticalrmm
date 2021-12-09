<#
.Synopsis
    Event Viewer - New User Notification
.DESCRIPTION
    Event Viewer Monitor - Notify when new Local user is created
.EXAMPLE
    365
.NOTES
    v1 dinger initial release
    v1.1 silversword adding parameter options 11/2021    
#>

$ErrorActionPreference = 'silentlycontinue'
if ($Args.Count -eq 0) {
    $TimeSpan = (Get-Date) - (New-TimeSpan -Day 1)
}
else {
    $TimeSpan = (Get-Date) - (New-TimeSpan -Day $param1)
}

if (Get-WinEvent -FilterHashtable @{LogName = 'security'; ID = '4720', '4720', '4728', '4732', '4756', '4767'; StartTime = $TimeSpan }) {
    Write-Output "A change has been made to local users"
    Get-WinEvent -FilterHashtable @{LogName = 'security'; ID = '4720', '4720', '4728', '4732', '4756', '4767'; StartTime = $TimeSpan }
    exit 1
}

else {
    Write-Output "No changes all looks fine"
    exit 0
}


Exit $LASTEXITCODE