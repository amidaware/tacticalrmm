#Update with command parameters

$PrintJobs = get-wmiobject -class "Win32_PrintJob" -namespace "root\CIMV2" -computername . | Where-Object {[System.Management.ManagementDateTimeConverter]::ToDateTime($_.TimeSubmitted) -lt (Get-Date).AddDays(-2)} 
foreach ($job in $PrintJobs) 
{    
#   Write-Host "Canceling job $($job.JobId)"    
    $job.Delete() 
} 
