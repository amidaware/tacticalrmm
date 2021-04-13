$ErrorActionPreference = 'silentlycontinue'
$aadchk = dsregcmd /status | Where-Object { $_ -match 'AzureAdJoined : ' } | ForEach-Object { $_.Trim() }

if ($aadchk -Eq 'AzureAdJoined : Yes') {
    Write-Output "Machine is Azure Ad Joined"
    exit 0
}

else {
    Write-Output "Machine is not Azure Ad Joined"
    exit 1
}


Exit $LASTEXITCODE