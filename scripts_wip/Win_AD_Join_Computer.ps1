$domain = "myDomain"
$password = "myPassword!" | ConvertTo-SecureString -asPlainText -Force
$username = "$domain\myUserAccount"
$credential = New-Object System.Management.Automation.PSCredential($username,$password)
Add-Computer -DomainName $domain -OUPath "OU=testOU,DC=domain,DC=Domain,DC=com" -Credential $credential -Restart