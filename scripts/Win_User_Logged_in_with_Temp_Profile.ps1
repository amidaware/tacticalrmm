$ErrorActionPreference= 'silentlycontinue'
$TimeSpan = (Get-Date) - (New-TimeSpan -Day 1)
if (Get-WinEvent -FilterHashtable @{LogName='Application';ID='1511';StartTime=$TimeSpan})
{
Write-Output "An account has been logged in with a Temporary profile"
Get-WinEvent -FilterHashtable @{LogName='Application';ID='1511';StartTime=$TimeSpan}
exit 1
}

else
{
Write-Output "All looks fine"
exit 0
}


Exit $LASTEXITCODE