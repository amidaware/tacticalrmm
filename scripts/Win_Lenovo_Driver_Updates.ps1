<#
.SYNOPSIS
    Install a third party tool to check for device drivers. It only installs drivers that can be run non-interactively and silent
.REQUIREMENTS
    Lenovo device is needed
.INSTRUCTIONS
    -
.NOTES
	V1.0 Initial Release by https://github.com/maltekiefer
#>

if (-not (Get-Module -ListAvailable -Name LSUClient)) {
    Install-Module -Name 'LSUClient'
}

# Install only packages that can be installed silently and non-interactively

$updates = Get-LSUpdate | Where-Object { $_.Installer.Unattended }
$updates | Save-LSUpdate -Verbose
$updates | Install-LSUpdate -Verbose