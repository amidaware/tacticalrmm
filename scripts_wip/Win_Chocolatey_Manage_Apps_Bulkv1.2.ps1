<#
      .SYNOPSIS
      This will install multiple software items using the chocolatey if defined, with rate limiting when run with Hosts parameter
      .DESCRIPTION
      For installing packages using chocolatey. If you're running against more than 10, include the Hosts parameter to limit the speed. If running on more than 30 agents at a time make sure you also change the script timeout setting.
      .PARAMETER Mode
      3 options: install, uninstall, or upgrade (default).
      .PARAMETER Hosts
      Use this to specify the number of computer(s) you're running the command on. This will dynamically introduce waits to try and minimize the chance of hitting rate limits (20/min) on the chocolatey.org site: Hosts 20
      .PARAMETER PackagesNames
      Use this to specify which software to install eg: -PackagesNames googlechrome,firefox,7zip
      .EXAMPLE
      -Hosts 20 -PackagesNames googlechrome
      .EXAMPLE
      -Hosts 20 -PackagesNames googlechrome,firefox,7zip
      .EXAMPLE
      -Mode upgrade -Hosts 50
      .EXAMPLE
      -Mode uninstall -PackagesNames googlechrome
      .EXAMPLE
      -Mode uninstall -PackagesNames googlechrome,firefox,7zip
      .NOTES
      9/2021 v1 Initial release by @silversword411 and @bradhawkins 
      11/14/2021 v1.1 Fixing typos and logic flow @silversword411
      12/22/2021 v1.2 Adding support to install, upgrade, remove multiple packages. Switching to upgrade instead of install by default @erifkard
  #>
 
param (
    [Int] $Hosts = "0",
    [array]$PackagesNames,
    [string] $Mode = "upgrade"
)
 
$ErrorCount = 0
 
if ($Mode -ne "upgrade" -and !$PackagesNames) {
    write-output "No choco package name provided, please include Example: `"-PackagesNames googlechrome`" `n"
    Exit 1
}
 
if ($Hosts -and $Hosts -ne "0") {
    $randrange = ($Hosts + 1) * 6
    Write-Output "Calculating rnd"
    Write-Output "randrange $randrange"
    $rnd = Get-Random -Minimum 1 -Maximum $randrange; 
    Write-Output "rnd=$rnd"
}
else {
    $rnd = "1"
    Write-Output "rnd set to 1 manually"
    Write-Output "rnd=$rnd"
}
foreach ($Package in $PackagesNames) {
    if ($Mode -eq "upgrade") {
        Write-Output "Starting Upgrade of $Package"
        Start-Sleep -Seconds $rnd; 
        choco upgrade -y $Package
        Write-Output "Running upgrade for $Package"
    }
    else { 
        write-output "Running install/uninstall mode $Package"
        Start-Sleep -Seconds $rnd;
        choco $Mode $Package -y
        Exit 0
    }
}
Exit $LASTEXITCODE