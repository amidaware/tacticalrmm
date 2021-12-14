<#
    .SYNOPSIS
    Restarts stuck printer jobs.

    .DESCRIPTION 
    Cycles through each printer and restarts any jobs that are stuck with error status.

    .NOTES
    Change Log
    ----------------------------------------------------------------------------------
    V1.0 Initial Release by https://github.com/bc24fl/tacticalrmm-scripts/

#>

$allPrinters = Get-Printer
foreach ($printer in $allPrinters) {
    $printJobs = Get-PrintJob -PrinterName $($printer.Name)
    if ($printJobs) {
        foreach ($job in $printJobs) {
            if ($job.JobStatus -match 'Error') {
		$stuckPrinterName = $job.PrinterName
		$stuckPrinterJob = $job.Id
		Write-Host "Restarting Job Id $stuckPrinterJob on printer $stuckPrinterName"
                Restart-PrintJob -InputObject $job
            }
        }
    }
}