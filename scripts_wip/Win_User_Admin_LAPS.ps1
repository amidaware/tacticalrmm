# From @subz needs comments, and parameters for New Admin. Merge/consolidate with other admin Local Administrator Password Scripts if possible

$ComputerName = (Get-CimInstance -ClassName Win32_ComputerSystem | select name).name
#####################################################################
$ChangeAdminUsername = $false
$NewAdminUsername = "LocalAdmin"
#####################################################################
add-type -AssemblyName System.Web
$LocalAdminPassword = [System.Web.Security.Membership]::GeneratePassword(24, 5)
If ($ChangeAdminUsername -eq $false) {
    Get-LocalUser -Name "Administrator" | Enable-LocalUser
    Set-LocalUser -name "Administrator" -Password ($LocalAdminPassword | ConvertTo-SecureString -AsPlainText -Force) -PasswordNeverExpires:$true
}
else {
    New-LocalUser -Name $NewAdminUsername -Password ($LocalAdminPassword | ConvertTo-SecureString -AsPlainText -Force) -PasswordNeverExpires:$true
    Add-LocalGroupMember -Group Administrators -Member $NewAdminUsername
    Disable-LocalUser -Name "Administrator"
}
if ($ChangeAdminUsername -eq $false ) { $username = "Administrator" } else { $Username = $NewAdminUsername }
write-host "The $($Username) account has been enabled on $($ComputerName) and a new password has been set:"
write-host "$($ComputerName)\$($Username)"
write-host "$($LocalAdminPassword)"