<#
.SYNOPSIS
    Rename computer.

.DESCRIPTION
    Rename domain and non domain joined computers.

.PARAMETER NewName
    Specifies the new computer name.

.PARAMETER Username
    Specifies the username with permission to rename a domain computer.  
    Required for domain joined computers.  
    Do not add the domain part like "Domain01\" to the username as that is already extracted and appended to the Rename-Computer cmdlet.

.PARAMETER Password
    Specifies the password for the username.  
    Required for domain joined computers.

.PARAMETER Restart
    Switch to force the computer to restart after a successful rename.

.OUTPUTS
    Results are printed to the console.

.EXAMPLE
    -NewName mynewname
    
.EXAMPLE
    -Username myuser -Password mypassword -NewName mynewname -Restart

.NOTES
    Change Log
    V1.0 Initial release
    V2.0 Added domain join
#>

param(
    [string] $Username,
    [string] $Password,
    [switch] $Restart,
    [string] $NewName
)

if (!$NewName) {
    Write-Host "-NewName parameter required."
    Exit 1
}

if ((Get-WmiObject win32_computersystem).partofdomain -eq $false) {
    # Rename Non Domain Joined Computer

    if ($Restart) {
        Rename-computer -NewName $NewName -Force -Restart
    }
    else {
        Rename-computer -NewName $NewName -Force
    }
    Write-Host "Attempted rename of computer to $NewName."
    
} 
else {
    # Rename Domain Joined Computer

    if (!$Username) {
        Write-Host "-Username parameter required on domain joined computers."
        Exit 1
    }
    
    if (!$Password) {
        Write-Host "-Password parameter required on domain joined computers."
        Exit 1
    }
    
    $securePassword = ConvertTo-SecureString -string $Password -asPlainText -Force

    $domainUsername = (Get-WmiObject Win32_ComputerSystem).Domain + "\$Username"
    
    $credential = New-Object System.Management.Automation.PSCredential($domainUsername, $securePassword)
    
    if ($Restart) {
        Rename-computer -NewName $NewName -DomainCredential $credential -Force -Restart
    }
    else {
        Rename-computer -NewName $NewName -DomainCredential $credential -Force
    }
    Write-Host "Attempted rename of domain computer to $NewName."
}