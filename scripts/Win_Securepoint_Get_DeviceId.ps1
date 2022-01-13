<#
.SYNOPSIS
    Give back the Securepoint Device id

.REQUIREMENTS
    Securepoint Antivirus Pro must be installed on the client

.INSTRUCTIONS
    -

.NOTES
	V1.0 Initial Release by https://github.com/maltekiefer

#>

$SecurepointDeviceId = (Get-Item -Path 'HKLM:\SOFTWARE\Ikarus\guardx\cloud').GetValue('DeviceId')

Write-Output $SecurepointDeviceId

Exit $LASTEXITCODE
