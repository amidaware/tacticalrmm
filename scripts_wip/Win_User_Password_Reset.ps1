# Set the Password-String -- defaults to THIS.IS.NOT.SECURE
$newpwd = ConvertTo-SecureString -String "THIS.IS.NOT.SECURE" -AsPlainText ?Force

# Set the correct local user you want to reset
$UserAccount = Get-LocalUser -Name "ADMINUSER"

# Set it
$UserAccount | Set-LocalUser -Password $newpwd