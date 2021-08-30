Write-host "Trusting PS Gallery"
Set-PSRepository -Name 'PSGallery' -InstallationPolicy Trusted

Write-Host "Installing PolicyFileEditor"
Install-Module -Name PolicyFileEditor 

$UserDir = "$env:windir\system32\GroupPolicy\User\registry.pol"

Write-Host "Setting inactivity timeout to 10 mins"
$RegPath = 'Software\Policies\Microsoft\Windows\CurrentVersion\Policies\System'
$RegName = 'InactivityTimeoutSecs '
$RegData = '600'
$RegType = 'DWord'
Set-PolicyFileEntry -Path $UserDir -Key $RegPath -ValueName $RegName -Data $RegData -Type $RegType

# apply the new policy immediately
gpupdate.exe /force