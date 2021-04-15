$ErrorActionPreference= 'silentlycontinue'
$TimeSpan = (Get-Date) - (New-TimeSpan -Day 1)
if (Get-WinEvent -FilterHashtable @{LogName='security';ID='4720','4720','4728','4732','4756','4767';StartTime=$TimeSpan})
{
Write-Output "A change has been made to local users"
Get-WinEvent -FilterHashtable @{LogName='security';ID='4720','4720','4728','4732','4756','4767';StartTime=$TimeSpan}
exit 1
}

else
{
Write-Output "No changes all looks fine"
exit 0
}


Exit $LASTEXITCODE