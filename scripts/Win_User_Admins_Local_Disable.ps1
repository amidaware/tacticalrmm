<#
    .SYNOPSIS
    Disables all local admins if joined to domain or AzureAD

    .DESCRIPTION 
    Checks to see if computer is either joined to a AD domain or Azure AD. If it is, it disables all local admin accounts. If not joined to domain/AzureAD, leaves local admin accounts in place

    .OUTPUTS
    Results are printed to the console.

    .NOTES
    Change Log
    5/12/2021 V1.0 Initial release

    Contributed by: https://github.com/dinger1986
#>

$ErrorActionPreference = 'silentlycontinue'

if (get-localuser | Where-Object Enabled) {
    if (dsregcmd /status | Where-Object { $_ -match 'DomainJoined : YES' } | ForEach-Object { $_.Trim() }) {
        Write-Output "Removing Local Admins"
        get-localuser | Where-Object Enabled | Disable-LocalUser
        get-localuser | Select name, Enabled
    }

    elseif (dsregcmd /status | Where-Object { $_ -match 'AzureAdJoined : YES' } | ForEach-Object { $_.Trim() }) {
        Write-Output "Removing Local Admins"
        get-localuser | Where-Object Enabled | Disable-LocalUser
        get-localuser | Select name, Enabled
    }

    else {
        Write-Output "Machine not on Domain so leaving local admins"
        get-localuser | Select name, Enabled
    }

}

else {
    Write-Output "No local Users"
}