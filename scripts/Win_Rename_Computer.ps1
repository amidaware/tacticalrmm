<#
.SYNOPSIS
    Rename computer.

.DESCRIPTION
    Rename domain / non domain joined computer.

.OUTPUTS
    Results are printed to the console.

.EXAMPLE
    PS C:\> .\Win_Rename_Computer.ps1 -username myuser -password mypassword -domain mydomain -newComputerName mynewcomputername -forceRestart

.NOTES
    Change Log
    V1.0 Initial release
    V2.0 Added domain join
#>

param(
    [string] $username,
    [string] $password,
    [string] $domain,
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
    Write-Host "Attempted rename computer to $newComputerName."
    
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
    
    if (!$domain){
        Write-Host "-domain parameter required on domain joined computers."
        Exit 1
    }
    
    $securePassword = ConvertTo-SecureString -string $password -asPlainText -Force
    
    $credential = New-Object System.Management.Automation.PSCredential($username, $securePassword)
    
    if ($forceRestart) {
        Rename-computer -NewName $newComputerName -DomainCredential $credential -Force -Restart
    } else {
        Rename-computer -NewName $newComputerName -DomainCredential $credential -Force
    }
    Write-Host "Attempted rename domain computer to $newComputerName."
}