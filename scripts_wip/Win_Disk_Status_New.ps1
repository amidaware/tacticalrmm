<#
      .SYNOPSIS
      Used to monitor Disk Health, returns error when having issues
      .DESCRIPTION
      Monitors the Event Viewer | System Log | For known Disk related errors. If no parameters are specified, it'll only search the last 1 day of event logs (good for a daily run/alert using Tasks and Automation)
      .PARAMETER Time
      Optional: If specified, it will search that number of days in the Event Viewer | System Logs
      .EXAMPLE
      -Time 365
      .NOTES
      4/2021 v1 Initial release by dinger1986
      11/2021 v1.1 Fixing missed bad sectors etc by silversword
  #>

param (
    [string] $Time = "1"
)

$ErrorActionPreference = 'silentlycontinue'
$TimeSpan = (Get-Date) - (New-TimeSpan -Day $Time)
# ID: 7     
# ID: 9     
# ID: 11    
# ID: 15    
# ID: 52    
# ID: 98    
# ID: 129   "Reset to device, \Device\RaidPort0, was issued."     Provider=storahci
# ID: 153   Bad Sectors aka "The IO operation at logical block address..."    ProviderName=disk
if (Get-WinEvent -FilterHashtable @{LogName = 'system'; ID = '7', '9', '11', '15', '52', '98', '129', '153'; Level = 1, 2, 3; ProviderName = '*disk*', '*storsvc*', '*ntfs*'; StartTime = $TimeSpan } -MaxEvents 10 ) {
    Write-Output "Disk errors detected please investigate"
    Get-WinEvent -FilterHashtable @{LogName = 'system'; ID = '7', '9', '11', '15', '52', '98', '129', '153'; Level = 1, 2, 3; ProviderName = '*disk*', '*storsvc*', '*ntfs*'; StartTime = $TimeSpan } | Format-List TimeCreated, Id, LevelDisplayName, Message
    exit 1
}

else {
    Write-Output "Disks are Healthy"
    exit 0
}

Exit $LASTEXITCODE