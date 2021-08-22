<#
.SYNOPSIS
    Rename computer.

.DESCRIPTION
    Rename domain and non domain joined computers.

.PARAMETER newComputerName
    Specifies the new computer name.

.PARAMETER username
    Specifies the username with permission to rename a domain computer.  
    Required for domain joined computers.  
    Do not add the domain part like "Domain01\" to the username as that is already extracted and appended to the Rename-Computer cmdlet.

.PARAMETER password
    Specifies the password for the username.  
    Required for domain joined computers.

.PARAMETER forceRestart
    Switch to force the computer to restart after a successful rename.

.OUTPUTS
    Results are printed to the console.

.EXAMPLE
    PS C:\> .\Win_Rename_Computer.ps1 -username myuser -password mypassword -newComputerName mynewcomputername -forceRestart

.NOTES
    Change Log
    V1.0 Initial release
    V2.0 Added domain join
#>

param(
    [string] $username,
    [string] $password,
    [switch] $forceRestart,
    [string] $newComputerName
)

if (!$newComputerName){
    Write-Host "-newComputerName parameter required."
    Exit 1
}

if ((Get-WmiObject win32_computersystem).partofdomain -eq $false) {
    # Rename Non Domain Joined Computer

    if ($forceRestart) {
        Rename-computer -NewName $newComputerName -Force -Restart
    } else {
        Rename-computer -NewName $newComputerName -Force
    }
    Write-Host "Attempted rename of computer to $newComputerName."
    
} else {
    # Rename Domain Joined Computer

    if (!$username){
        Write-Host "-username parameter required on domain joined computers."
        Exit 1
    }
    
    if (!$password){
        Write-Host "-password parameter required on domain joined computers."
        Exit 1
    }
    
    $securePassword = ConvertTo-SecureString -string $password -asPlainText -Force

    $domainUsername = (Get-WmiObject Win32_ComputerSystem).Domain + "\$username"
    
    $credential = New-Object System.Management.Automation.PSCredential($domainUsername, $securePassword)
    
    if ($forceRestart) {
        Rename-computer -NewName $newComputerName -DomainCredential $credential -Force -Restart
    } else {
        Rename-computer -NewName $newComputerName -DomainCredential $credential -Force
    }
    Write-Host "Attempted rename of domain computer to $newComputerName."
}