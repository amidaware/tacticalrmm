$ErrorActionPreference = 'silentlycontinue'

if (Get-Module -ListAvailable -Name NuGet) {
    Write-Host "NuGet exists"
} 
else {
    Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Force
}

if (Get-Module -ListAvailable -Name PSWindowsUpdate) {
    Write-Host "PSWindowsUpdate exists"
} 
else {
    Install-Module -Name PSWindowsUpdate -force 
}

Set-ExecutionPolicy -ExecutionPolicy Unrestricted
Get-WindowsUpdate -install -acceptall