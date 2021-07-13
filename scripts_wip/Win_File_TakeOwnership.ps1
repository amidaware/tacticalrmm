###########################################################################################
#Take Ownership / Set Folder Permissions v1.0
#By Alan O'Brien
#Line 8,11,13 + 14: Change the path to the folder that you want to take full control of
#Line 9: Change to whatever account you want applied to the folder to take ownership of it
#Final line will show if the permission applied correctly
###########################################################################################
$ACL = Get-Acl -Path "C:\Users\XXX\XXX\Desktop"
$User = New-Object System.Security.Principal.Ntaccount("BUILTIN\Administrators")
$ACL.SetOwner($User)
$ACL | Set-Acl -Path "C:\Users\XXX\XXX\Desktop"
$ACL.SetAccessRuleProtection($true, $true)
$ACL = Get-Acl -Path "C:\Users\XXX\XXX\Desktop"
Get-ACL -Path "C:\Users\XXX\XXX\Desktop"