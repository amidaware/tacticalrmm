<#
      .SYNOPSIS
      Used to enable or disable users
      .DESCRIPTION
      For installing packages using chocolatey. If you're running against more than 10, include the Hosts parameter to limit the speed. If running on more than 30 agents at a time make sure you also change the script timeout setting.
      .PARAMETER Name
      Required: Username
      .PARAMETER Enabled
      Required: yes/no
      .EXAMPLE
      -Name user -Enabled no
      .NOTES
      11/15/2021 v1 Initial release by @silversword411
  #>

param (
    [string] $Name,
    [string] $Enabled
)

if (!$Enabled -or !$Name) {
    write-output "Missing required parameters. Please include Example: `"-Name username - -Enabled yes/no`" `n"
    Exit 1
}
else {
    net user $Name /active:$Enabled
    Write-Output "$Name set as active:$Enabled"
    Exit 0
}
