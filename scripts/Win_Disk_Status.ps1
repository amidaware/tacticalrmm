# Checks local disks for errors reported in event viewer within the last 24 hours

$ErrorActionPreference = 'silentlycontinue'
$TimeSpan = (Get-Date) - (New-TimeSpan -Day 1)
if (Get-WinEvent -FilterHashtable @{LogName = 'system'; ID = '11', '9', '15', '52', '129', '7', '98'; Level = 2, 3; ProviderName = '*disk*', '*storsvc*', '*ntfs*'; StartTime = $TimeSpan } -MaxEvents 10 | Where-Object -Property Message -Match Volume*)
{
    Write-Output "Disk errors detected please investigate"
    Get-WinEvent -FilterHashtable @{LogName = 'system'; ID = '11', '9', '15', '52', '129', '7', '98'; Level = 2, 3; ProviderName = '*disk*', '*storsvc*', '*ntfs*'; StartTime = $TimeSpan }
    exit 1
}


else {
    Write-Output "Disks are Healthy"
    exit 0
}


Exit $LASTEXITCODE
