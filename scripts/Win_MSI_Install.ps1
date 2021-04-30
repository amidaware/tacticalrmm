Function Install-MSI {
    Param (
        [Parameter(Mandatory, ValueFromPipeline = $true)]
        [ValidateNotNullOrEmpty()]
        [System.IO.FileInfo]$File,
        [String[]]$AdditionalParams,
        [Switch]$OutputLog
    )
    $DataStamp = get-date -Format yyyyMMddTHHmmss
    $logFile = "$($env:programdata)\CentraStage\MilesRMM\{0}-{1}.log" -f $file.fullname, $DataStamp
    $MSIArguments = @(
        "/i",
        ('"{0}"' -f $file.fullname),
        "/qn",
        "/norestart",
        "/L*v",
        $logFile
    )
    if ($additionalParams) {
        $MSIArguments += $additionalParams
    }
    Start-Process "msiexec.exe" -ArgumentList $MSIArguments -Wait -NoNewWindow 
    if ($OutputLog.IsPresent) {
        $logContents = get-content $logFile
        Write-Output $logContents
    }
}