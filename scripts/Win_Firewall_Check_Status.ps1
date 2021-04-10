$ErrorActionPreference = 'silentlycontinue'
$fwenabled = (get-netfirewallprofile -policystore activestore).Enabled

if ($fwenabled.Contains('True')) {
    Write-Output "Firewall is Enabled"
    netsh advfirewall show currentprofile
    exit 0
}


else {
    Write-Host "Firewall is Disabled"
    exit 1
}


Exit $LASTEXITCODE