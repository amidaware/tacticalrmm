# For TRMM need to be able to handle all 3 TRMM url's at once. Add these command parameters. Should probably include with howto doc that will use Key Store default recommended keys eg
# rmmurl would be {{global.rmmurl}}
# meshurl would be {{global.meshurl}}
# apiurl would be {{global.apiurl}}
# rmmip would be {{global.rmmip}}
# -allip (does all) 3 URL's with same IP
# -rmmurl
# -meshurl
# -apiurl
# -rmmip
# -meship
# -apiip



# By Tom Chantler - https://tomssl.com/2019/04/30/a-better-way-to-add-and-remove-windows-hosts-file-entries/
param([bool]$CheckHostnameOnly = $false)
$DesiredIP = $IP
$Hostname = $URL

# Adds entry to the hosts file.
#Requires -RunAsAdministrator
$hostsFilePath = "$($Env:WinDir)\system32\Drivers\etc\hosts"
$hostsFile = Get-Content $hostsFilePath

Write-Host "About to add $desiredIP for $Hostname to hosts file" -ForegroundColor Gray

$escapedHostname = [Regex]::Escape($Hostname)
$patternToMatch = If ($CheckHostnameOnly) { ".*\s+$escapedHostname.*" } Else { ".*$DesiredIP\s+$escapedHostname.*" }
If (($hostsFile) -match $patternToMatch) {
    Write-Host $desiredIP.PadRight(20, " ") "$Hostname - not adding; already in hosts file" -ForegroundColor DarkYellow
} 
Else {
    Write-Host $desiredIP.PadRight(20, " ") "$Hostname - adding to hosts file... " -ForegroundColor Yellow -NoNewline
    Add-Content -Encoding UTF8  $hostsFilePath ("$DesiredIP".PadRight(20, " ") + "$Hostname")
    Write-Host " done"
}