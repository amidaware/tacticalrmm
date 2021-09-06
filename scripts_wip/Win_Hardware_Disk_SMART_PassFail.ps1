$ErrorActionPreference= 'silentlycontinue'
$smartst = (Get-WmiObject -namespace root\wmi -class MSStorageDriver_FailurePredictStatus).PredictFailure

if ($smartst = 'False') 
{
Write-Output "Theres no SMART Failures predicted"
exit 0
}


else
{
Write-Output "There are SMART Failures detected"
exit 1
}


Exit $LASTEXITCODE