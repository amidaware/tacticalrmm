function Update-ChocoApps {
  <#
  .SYNOPSIS
    Update choco apps and removes the newly created shortcuts.

  .DESCRIPTION
    Update choco apps and removes the newly created shortcuts.
    Requires administrator privileges.

  .NOTES
    Author:   Chris Stafford
    Version:  1.0.5
    Created:  2020.06.17
    Modified: 2020.08.06
  #>

  # Require Admin Permissions
  $IsAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
  
  if ($IsAdmin -eq $false) {
    Write-Warning 'Admin Rights Required'
    break
  }

  $StartTime = Get-Date

  # Aborts if Chocolatey is not installed
  if (Test-Path 'C:\ProgramData\chocolatey\choco.exe') {
    # Locations for shortcuts to remove
    $Desktops = "$env:PUBLIC\Desktop", "$env:USERPROFILE\Desktop"

    $Choco = 'C:\ProgramData\chocolatey\choco.exe'
    
    # Parse outdated app names from choco (leave the space in ' Outdated*')
    Write-Output 'Searching for Outdated Apps'
    $AppList = & $Choco outdated --limit-output | ForEach-Object { $_.Split('|')[0] }
    
    # Skips if no apps are outdated
    if ($AppList.Count -gt 0) {
      foreach ($App in $AppList) { 
        # upgrade app
        & $Choco upgrade $App --confirm --limit-output --no-progress
        
        if ($App -like '*.install') {
          $App = $App.Split('.')[0]
        }
        # removes shortcut (created by install) based on the app name and time created
        Write-Output "Removing Shortcut: $App"
        $Desktops | Get-ChildItem -Filter "*.lnk" -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -gt $StartTime } | Remove-Item
      }
    }
    else {
      Write-Output 'No Outdated Apps'
    }
  }
  else {
    Write-Output 'Chocolatey is not installed'
  }
}

Update-ChocoApps