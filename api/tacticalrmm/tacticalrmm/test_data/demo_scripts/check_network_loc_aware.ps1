$networkstatus = Get-NetConnectionProfile | Select NetworkCategory | Out-String

if ($networkstatus.Contains("DomainAuthenticated")) {
    exit 0
} else {
    exit 1
}