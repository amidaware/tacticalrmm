<#
.SYNOPSIS
    Enables Bitlocker

.DESCRIPTION
    Enables bitlocker, and shows recovery keys

.OUTPUTS
    Results are printed to the console.

.NOTES
    Change Log
    V1.0 Initial release from dinger1986 https://discord.com/channels/736478043522072608/744281869499105290/836871708790882384
#>

If(!(test-path C:\TEMP\))
{
      New-Item -ItemType Directory -Force -Path C:\TEMP\
}

Enable-Bitlocker -MountPoint c: -UsedSpaceOnly -SkipHardwareTest -RecoveryPasswordProtector
manage-bde -protectors C: -get

$bitlockerkey = manage-bde -protectors C: -get
(
echo $bitlockerkey
)>"C:\Temp\bitlockerkey.txt"