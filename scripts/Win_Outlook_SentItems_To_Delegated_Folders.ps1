<#
.Synopsis
   Outlook - Delegated folders set for all profiles
.DESCRIPTION
   Uses RunAsUser to setup sent items for the currently logged on user on delegated folders to go into the delegated folders sent for all. 
   Applies to Office 2016 and later, modify reg key for older versions of office.
   https://docs.microsoft.com/en-us/outlook/troubleshoot/email-management/email-remains-in-the-outbox-when-you-use-the-deleg
.NOTES
   v1.0 
   Submitted by: https://github.com/dinger1986
#>

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

Invoke-AsCurrentUser -scriptblock {
    # Modify below for other versions of Office
    $regpath = 'Software\Microsoft\Office\16.0\Outlook\Preferences'
    $regname = "DelegateSentItemsStyle"
    $regvalue = "1"
    $regproperty = "Dword"
    New-ItemProperty -Path HKCU:\$regpath -Name $regname -Value $regvalue  -PropertyType $regproperty
}

Write-Output "Successfully changed Sent Items for Delegated folders"

$curpsxpol = Get-Content -Path $env:programdata\TacticalRMM\temp\curpsxpolicy.txt;
    
Set-ExecutionPolicy -ExecutionPolicy $curpsxpol