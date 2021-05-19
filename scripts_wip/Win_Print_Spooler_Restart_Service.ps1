<#
.Synopsis
   Restart Print Spooler Service
.DESCRIPTION
   Will force-restart the spooler service. With additional command parameter will also delete any pending print jobs
.EXAMPLE
   Another example of how to use this cmdlet
.OUTPUTS
   Any print jobs that are deleted
.NOTES
   v1.0 5/2021
   https://github.com/silversword411
.FUNCTIONALITY
   Print Spooler Troubleshooting, restarts spooler service. Can also delete all print jobs that are pending 
#>

#Restart Spooler service
Restart-Service -Name spooler -Force 

#Deletes All print jobs within the last 15 years
$PrintJobs = get-wmiobject -class "Win32_PrintJob" -namespace "root\CIMV2" -computername . | Where-Object { [System.Management.ManagementDateTimeConverter]::ToDateTime($_.TimeSubmitted) -lt (Get-Date).AddDays(-5500) } 
foreach ($job in $PrintJobs) {    
    #   Write-Host "Canceling job $($job.JobId)"    
    $job.Delete() 
}