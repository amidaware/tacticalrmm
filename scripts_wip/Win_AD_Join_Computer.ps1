<#
    .SYNOPSIS
    I do this

    .DESCRIPTION 
    I really do a lot of this

    .OUTPUTS
    Results are printed to the console. Future releases will support outputting to a log file. 

    .NOTES
    Change Log
    V1.0 Initial release

    Reference Links: www.google.com
#>

$domain = "myDomain"
$password = "myPassword!" | ConvertTo-SecureString -asPlainText -Force
$username = "$domain\myUserAccount"
$credential = New-Object System.Management.Automation.PSCredential($username, $password)
Add-Computer -DomainName $domain -OUPath "OU=testOU,DC=domain,DC=Domain,DC=com" -Credential $credential -Restart