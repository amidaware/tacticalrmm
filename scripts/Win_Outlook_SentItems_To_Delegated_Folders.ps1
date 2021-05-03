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

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$regpath = HKCU:\Software\Microsoft\Office\16.0\Outlook\Preferences
$regname = DelegateSentItemsStyle
$regvalue = 1
$regproperty = Dword


If (!(test-path '%ProgramData%\Tactical RMM\temp')) {
    New-Item -ItemType Directory -Force -Path '%ProgramData%\Tactical RMM\temp'
}

If (!(test-path C:\TEMP\curpsxpolicy.txt)) {
    $curexpolicy = Get-ExecutionPolicy

    (
        echo $curexpolicy
    )>"%ProgramData%\Tactical RMM\temp\curpsxpolicy.txt"
}

Set-ExecutionPolicy -ExecutionPolicy Unrestricted

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

Invoke-AsCurrentUser -scriptblock {
    New-ItemProperty -Path "$regpath" -Name "$regname" -Value "$regvalue"  -PropertyType "$regproperty"
}

Write-Output "Successfully changed Sent Items for Delegated folders"

$curpsxpol = Get-Content -Path "%ProgramData%\Tactical RMM\temp\curpsxpolicy.txt";
    
Set-ExecutionPolicy -ExecutionPolicy $curpsxpol

del "%ProgramData%\Tactical RMM\temp\curpsxpolicy.txt"