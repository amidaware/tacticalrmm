# Use as check script for old Powershell version 2.0 (aka Win7) and upgrade using https://github.com/wh1te909/tacticalrmm/blob/develop/scripts_wip/Win_Powershell_Upgrade.ps1

if ($PSVersionTable.PSVersion.Major -gt 2) {
    $PSVersionTable.PSVersion.Major
    Write-Output "PSVersion Greater than 2.0"
    exit 0
}
else {
    $PSVersionTable.PSVersion.Major
    Write-Output "PSVersion less than 2.0"
    exit 1
}