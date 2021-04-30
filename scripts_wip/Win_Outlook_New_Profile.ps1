# Script to create a new empty Outlook profile
# http://powershell-tools.com/exchange-outlook/create-new-outlook-profile-using-powershell/

$ofc = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
$OfficeInstall = Get-ChildItem -Path $ofc -Recurse | Where-Object {
  $_.GetValue('DisplayName') -like "Microsoft Office*" -or $_.GetValue('DisplayName') -like "Microsoft 365 Apps*"
}

# We only care about the major and minor version for the next part
$Version = $OfficeInstall.GetValue('DisplayVersion')[0..3] -join ""
$RegPath = "HKCU:\SOFTWARE\Microsoft\Office\$Version\Outlook"

New-Item -Path "$RegPath\Profiles" -Name "NewProfile"
Set-ItemProperty -Path $RegPath -Name "DefaultProfile" -Value "NewProfile"
Write-Host "Restart Outlook to setup new profile"