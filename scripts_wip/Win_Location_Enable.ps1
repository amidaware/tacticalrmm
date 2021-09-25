<#
.SYNOPSIS
    Enables Location services in Windows

.DESCRIPTION
    Lets you enable/disable device-wide location or User App location

.PARAMETER Enable
    https://www.tenforums.com/tutorials/13225-turn-off-location-services-windows-10-a.html
    user = Enable for User App locations
    machine = Enable location for system wide
    all = Enables both user and machine

.PARAMETER Disable
    https://www.tenforums.com/tutorials/13225-turn-off-location-services-windows-10-a.html
    user = Disable for User App locations
    machine = Disable location for system wide
    all = Disables both user and machine

.OUTPUTS
    Results are printed to the console.

.EXAMPLE
    -Enable machine
    
.EXAMPLE
    -Disable all

.NOTES
    Change Log
    V1.0 Initial release
#>


param (
    [string] $Enable,
    [string] $Disable
)


# HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location
if (Get-PackageProvider -Name NuGet) {
    Write-Output "NuGet Already Added"
} 
else {
    Write-Host "Installing NuGet"
    Install-PackageProvider -Name NuGet -Force
} 
 
if (Get-Module -ListAvailable -Name RunAsUser) {
    Write-Output "RunAsUser Already Installed"
} 
else {
    Write-Output "Installing RunAsUser"
    Install-Module -Name RunAsUser -Force
}

If (!(test-path $env:programdata\TacticalRMM\temp\)) {
    New-Item -ItemType Directory -Force -Path $env:programdata\TacticalRMM\temp\
}

If (!(test-path $env:programdata\TacticalRMM\temp\curpsxpolicy.txt)) {
    $curexpolicy = Get-ExecutionPolicy

    (
        Write-Output $curexpolicy
    )>$env:programdata\TacticalRMM\temp\curpsxpolicy.txt
}
Set-ItemProperty -Path HKLM:\SOFTWARE\Microsoft\PowerShell\1\ShellIds\Microsoft.PowerShell -Name ExecutionPolicy -Value Unrestricted

if (!$Enable -AND !$Disable) {
    Write-Host "At least one parameter is required: Enable or Disable."
    Exit 1
}

# Used to pull variables in and use them inside the script block. Contains message to show user
Set-Content -Path c:\temp\message.txt -Value $args

Invoke-AsCurrentUser -scriptblock {
    Write-Output "Runasuser started" | Out-File -append -FilePath c:\temp\raulog.txt
    $Enable = Get-Content -Path c:\temp\message.txt
    Write-Output $Enable | Out-File -append -FilePath c:\temp\raulog.txt
    Write-Output "$Enable" | Out-File -append -FilePath c:\temp\raulog.txt
    Write-Output "Debug output finished" | Out-File -append -FilePath c:\temp\raulog.txt

    if ($Enable -eq "user" -or $Enable -eq "all") {
        # https://www.tenforums.com/tutorials/13225-turn-off-location-services-windows-10-a.html
        $registryPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location"
        $Name = "Value"
        $value = "Allow"
        New-ItemProperty -Path $registryPath -Name $name -Value $value -PropertyType String -Force | Out-Null
        Write-Output "Enabled Location for user" | Out-File -append -FilePath c:\temp\raulog.txt
    }
    elseif ($Disable -eq "user" -or $Disable -eq "all") {
        $registryPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location"
        $Name = "Value"
        $value = "Deny"
        New-ItemProperty -Path $registryPath -Name $name -Value $value -PropertyType String -Force | Out-Null
        Write-Output "Disabled Location for user" | Out-File -append -FilePath c:\temp\raulog.txt
    }

}

$exitcode = Get-Content -Path "c:\temp\raulog.txt"
Write-Host $exitcode


$curpsxpol = Get-Content -Path $env:programdata\TacticalRMM\temp\curpsxpolicy.txt;
Set-ExecutionPolicy -ExecutionPolicy $curpsxpol

if ($Enable -eq "machine" -or $Enable -eq "all") {
    # https://www.tenforums.com/tutorials/13225-turn-off-location-services-windows-10-a.html
    $registryPath = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location"
    $Name = "Value"
    $value = "Allow"
    New-ItemProperty -Path $registryPath -Name $name -Value $value -PropertyType String -Force | Out-Null
    Write-Output "Enabled Location for machine"
}

if ($Disable -eq "machine" -or $Disable -eq "all") {
    $registryPath = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location"
    $Name = "Value"
    $value = "Deny"
    New-ItemProperty -Path $registryPath -Name $name -Value $value -PropertyType String -Force | Out-Null
    Write-Output "Disabled Location for machine"
}

Remove-Item -path "c:\temp\raulog.txt"