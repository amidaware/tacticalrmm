$ErrorActionPreference = 'silentlycontinue'
$fwenabled = (get-netfirewallprofile -policystore activestore).Enabled

if ($fwenabled.Contains('False')) {
    Write-Output "Firewall is Disabled"
    exit 1
}


else {
    Write-Host "Firewall is Enabled"
    netsh advfirewall show currentprofile
    exit 0
}


Exit $LASTEXITCODE
