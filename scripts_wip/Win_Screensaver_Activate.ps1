<#
    .SYNOPSIS
        Lets you enable/disable screensaver and set options

    .DESCRIPTION
        You can enable and disable the screensaver, Set Timeout, Require password on wake, and change default screensaver

    .PARAMETER Active
        1 = Enable screensaver
        0 = Disable screensaver

    .PARAMETER Timeout
        Number in Minutes

    .PARAMETER IsSecure
        1 = Requires password after screensaver activates
        0 = Disabled password requirement

    .PARAMETER ScreensaverName
        Can optionally use any of these default windows screensavers: scrnsave.scr (blank), ssText3d.scr, Ribbons.scr, Mystify.scr, Bubbles.scr

    .EXAMPLE
        Active 1 Timeout 60 IsSecure 0 Name Bubbles.scr

    .EXAMPLE
        Active 0
        
    .NOTES
        Change Log
        V1.0 Initial release
#>

param (
    [string] $Active,
    [string] $Timeout,
    [string] $IsSecure,
    [string] $ScreensaverName
)


# Enable screensaver
Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name ScreenSaveActive -Value $Active

# Screensaver Timeout Value
Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name ScreenSaveTimeOut -Value $Timeout

# On resume, display logon screen. 
Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name ScreenSaveIsSecure -Value $IsSecure

# Set Screensaver to blank if not specified
if (!$ScreensaverName) {
    Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name scrnsave.exe -Value "c:\windows\system32\scrnsave.scr"
    Exit 0
}
else {
    Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name scrnsave.exe -Value "c:\windows\system32\$ScreensaverName"
    Exit 0
}


