<#
	.SYNOPSIS
	Checks drive to see if bitlocker is enabled
	.DESCRIPTION
	Assumes c, but you can specify a drive if you want.
	.PARAMETER Drive
	Optional: Specify drive letter if you want to check a drive other than c
	.EXAMPLE
	Drive d
	.NOTES
	9/20/2021 v1 Initial release by @silversword411 with the help of @Ruben
#>

param (
	[string] $Drive = "c"
)


if ((Get-BitLockerVolume -MountPoint $Drive).ProtectionStatus -eq 'On') {
	do {
		$EncryptionPercentage = (Get-BitLockerVolume -MountPoint $Drive).EncryptionPercentage
		Write-Output "BitLocker Encryption Percentage: $EncryptionPercentage"
		Start-Sleep -Seconds 5
	} until ($EncryptionPercentage -match 100)
	Write-Output "Bitlocker is enabled and Encryption completed"
	Exit 0
}
else {
	Write-Output "BitLocker is not turned on for this volume!"
	Exit 1
}
