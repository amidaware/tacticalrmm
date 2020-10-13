## Copied from https://github.com/ThatsNASt/tacticalrmm to add to new pull request for https://github.com/wh1te909/tacticalrmm
## Remvoed the use of the alias sleep, replaced with Start-Sleep.
$ErrorActionPreference = "Stop"
$log = "BitlockerReport.txt"
#Sleep to allow the report to run first as DSC
Start-Sleep 20

#Function to archive old reports so that the Dash can read recent events
$newlog = "BitlockerReportArchive.txt"
$archived = ("{0}_{1}" -f (Get-Date -f d), $newlog)
$archived = $archived.Replace("/", "-")
$exists = Test-Path -Path $log
$logsize = (Get-Item $log).length
function RunArchive {
    if ($logsize -gt 100kb) {
        Rename-Item $log $archived
        Try {
            New-Item -ItemType directory -Path "Archive"
        }
        Catch {
        }
        Move-Item $archived -Destination "Archive" -Force
        Write-Host "Log file has been archived."
        Write-Host "Script Check Passed"
        exit 0
        if (!$exists) {
            Write-Host "Could not find log file to archive."
            exit 1001
        }
    }
    if ($logsize -lt 100kb) {
        Write-Host "Log size in bytes: $logsize"
    }
}

#Actually retrieve the report and read it back
Try {
    Write-Output ("`n{0} - {1}" -f (Get-Date), "Retrieving bitlocker report log....`n") 
    Get-Content "BitlockerReport.txt" | Write-Host
    RunArchive
    Write-Host "Script Check Passed"
    exit 0
}
Catch {
    Write-Host "Could not get bitlocker report."
    Write-Host $Error[0]
    exit 1002
}

exit $LASTEXITCODE 