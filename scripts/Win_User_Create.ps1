<#
    .SYNOPSIS
    Creates Local User on computer

    .DESCRIPTION 
    Creates a Local user with password and adds to Users group. If group specificed you can add to a different group

    .OUTPUTS
    Results are printed to the console.

    .EXAMPLE
    In parameter set desired items
        -username testuser -password password -description "Big Bozz" -group administrators

    .NOTES
    Change Log
    6/17/2021 V1.0 Initial release
    6/17/2021 v1.1 Adding group support

    Contributed by: https://github.com/brodur
    Tweaks by: https://github.com/silversword411
#>

param(
    $username, 
    $password, 
    $description = "User added by TacticalRMM", 
    $fullname = "",
    $group
)

if ([string]::IsNullOrEmpty($username)) {
    Write-Output "Username must be defined. Use -username <value> to pass it."
    EXIT 1
}

if ([string]::IsNullOrEmpty($password)) {
    Write-Output "Password must be defined. Use -password <value> to pass it."
    EXIT 1
}
else {
    $password = ConvertTo-SecureString -String $password -AsPlainText -Force
}


try {
    New-LocalUser -Name $username -Password $password -Description $description -PasswordNeverExpires -FullName $fullname
    if ([string]::IsNullOrEmpty($group)) {
        Add-LocalGroupMember -Group "Users" -Member $username
        Write-Output "Adding user to the User Group"
    }
    else {
        Add-LocalGroupMember -Group $group -Member $username
        Write-Output "Adding user to the $group Group"
    }
    EXIT 0
}
catch {
    Write-Output "An error has occured."
    Write-Output $_
    EXIT 1
}

EXIT $LASTEXITCODE