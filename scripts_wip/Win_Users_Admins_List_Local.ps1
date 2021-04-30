Write-Output ("Members of Administrators on " + (hostname) + ":")

try {
    # the Get-LocalGroupMember cmdlet will get a list of local admins for us, but, there are some bugs in the code and so in some cases, like if there are AzureAD accounts in the local admins group, it will fail, thus we can fall back to using net localgroup
    $admins = Get-LocalGroupMember -Group "Administrators" -ErrorAction Stop # erroraction stop so that we can break out of this try and go to catch in case the cmdlet fails
    ForEach ($admin in $admins) {
        if ($admin.PrincipalSource.ToString() -eq "Local") { # if it's a local account, we can check if the account is enabled
            $enabled = (Get-LocalUser -Name ($admin.Name -Split "\\")[1]).Enabled # split the computername, etc off the front of the username and use Get-LocalUser to check if enabled
            Write-Output ($admin.Name + " (Account Enabled: " + $enabled + ")")
        } else {
            Write-Output ($admin.Name + " (Unable to check if enabled, source is " + $admin.PrincipalSource + ")") # if it isn't a local account, just like the source along with it
        }
    }
} catch { # fall back to listing with net localgroup if Get-LocalGroupMember fails
    write-output ("Get-LocalGroupMember failed, falling back to net localgroup Administrators")
    $admins = net localgroup "Administrators"
    $length = $admins.length
    $admins = $admins[6..($length - 3)]
    ForEach ($admin in $admins) {
        Get-LocalUser -Name $admin
    }
}