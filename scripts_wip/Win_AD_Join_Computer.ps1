<#
    .SYNOPSIS
    Joins computer to Active Directory.

    .DESCRIPTION 
    Computer can be joined to AD in a specific OU specified in the parameters or it will join the default location.

    .OUTPUTS
    Results are printed to the console. Future releases will support outputting to a log file.
    
    .NOTES
    Change Log
    V1.0 Initial release
    V1.1 Parameterization; Error Checking with conditionals and exit codes

    Reference Links: 
        www.google.com
        docs.microsoft.com
#>

param(
    $domain,
    $password,
    $UserAccount,
    $OUPath
)

$username = "$domain\$UserAccount"
$credential = New-Object System.Management.Automation.PSCredential($username, $password)

if ([string]::IsNullOrEmpty($domain)) {
    Write-Output "Domain must be defined. Use -domain <value> to pass it."
    EXIT 1
}

if ([string]::IsNullOrEmpty($UserAccount)) {
    Write-Output "User Account must be defined. Use -UserAccount <value> to pass it."
    EXIT 1
}

if ([string]::IsNullOrEmpty($password)){
    Write-Output "Password must be defined. Use -password <value> to pass it."
    EXIT 1
}

else{
    $password = ConvertTo-SecureString -string $password -asPlainText -Force
}

try{

if ([string]::IsNullOrEmpty($OUPath){
    Write-Output "OU Path is not defined. Computer object will be created in the default OU."
    Add-Computer -DomainName $domain -Credential $credential -Restart
    EXIT 0
}

else {
    Add-Computer -DomainName $domain -OUPath $OUPath -Credential $credential -Restart
    EXIT 0
}
}

catch{
    Write-Output "An error has occured."
    EXIT 1
}

Exit $LASTEXITCODE