<#
.Synopsis
    Bluescreen - Reports bluescreens
.DESCRIPTION
    This will check for Bluescreen events on your system. If parameter provided, goes back that number of days
.EXAMPLE
    365
.NOTES
    v1 bbrendon 2/2021
    v1.1 silversword updating with parameters 11/2021    
#>


$param1 = $args[0]

$ErrorActionPreference = 'silentlycontinue'
if ($Args.Count -eq 0) {
    $TimeSpan = (Get-Date) - (New-TimeSpan -Day 1)
}
else {
    $TimeSpan = (Get-Date) - (New-TimeSpan -Day $param1)
}


if (Get-WinEvent -FilterHashtable @{LogName = 'application'; ID = '1001'; ProviderName = 'Windows Error Reporting'; Level = 4; Data = 'BlueScreen'; StartTime = $TimeSpan }) {
    Write-Output "There has been bluescreen events detected on your system"
    Get-WinEvent -FilterHashtable @{LogName = 'application'; ID = '1001'; ProviderName = 'Windows Error Reporting'; Level = 4; Data = 'BlueScreen'; StartTime = $TimeSpan }
    exit 1
}

{
    else 
    Write-Output "No bluescreen events detected in the past 24 hours."
    exit 0
}

Exit $LASTEXITCODE
