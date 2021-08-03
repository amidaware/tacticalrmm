<#
      .SYNOPSIS
      This will install software using the chocolatey, with rate limiting when run with Hosts parameter
      .DESCRIPTION
      For installing packages using chocolatey. If you're running against more than 10, include the Hosts parameter to limit the speed. If running on more than 30 agents at a time make sure you also change the script timeout setting.
      .PARAMETER Mode
      3 options: install (default), uninstall, or upgrade.
      .PARAMETER Hosts
      Use this to specify the number of computer(s) you're running the command on. This will dynamically introduce waits to try and minimize the chance of hitting rate limits (20/min) on the chocolatey.org site: Hosts 20
      .PARAMETER PackageName
      Use this to specify which software to install eg: PackageName googlechrome
      .EXAMPLE
      Hosts 20 PackageName googlechrome
      .EXAMPLE
      Mode upgrade Hosts 50
      .EXAMPLE
      Mode uninstall PackageName googlechrome
  #>

param (
    [string] $Hosts = "0",
    [string] $PackageName,
    [string] $Mode = "install",
)

$ErrorCount = 0

if (!$PackageName) {
    write-output "No choco package name provided, please include Example: `"PackageName googlechrome`" `n"
    $ErrorCount += 1
}

if (!$Mode -eq "upgrade") {
    $randrange = ($Hosts + 1) * 10
    $rnd = Get-Random -Minimum 1 -Maximum $randrange; 
    Start-Sleep -Seconds $rnd; 
    choco ugrade -y all
    Write-Output "Running upgrade"
    Exit 0
}

if (!$Hosts -eq "0") {
    write-output "No Hosts Specified, running concurrently"
    choco $Mode $PackageName -y
    Exit 0
}
else {
    $randrange = ($Hosts + 1) * 6
    $rnd = Get-Random -Minimum 1 -Maximum $randrange; 
    Start-Sleep -Seconds $rnd; 
    choco $Mode $PackageName -y
    Exit 0
}

Exit $LASTEXITCODE