<#
.Synopsis
   Allows listing, finding and uninstalling most software on Windows. There will be a best effort to uninstall silently if the silent
  uninstall string is not provided.
.DESCRIPTION
  Allows listing, finding and uninstalling most software on Windows. There will be a best effort to uninstall silently if the silent
  uninstall string is not provided.
.INPUTS
  -list Will list all installed 32-bit and 64-bit software installed on the target machine.
  -list "<software name>" will find a particular application installed giving you the uninstall string and quiet uninstall string if it exists
  -list "<software name>" -u "<uninstall string>" will allow you to uninstall the software from the Windows machine silently
  -list "<software name>" -u "<quiet uninstall string>" will allow you to uninstall the software from the Windows machine silently
.EXAMPLE
  Follow the steps below via script arguments to find and then uninstall VLC Media Player.
  Step 1: -list "vlc"
  Step 1 result:
    1 results 
    ********** 
    Name: VLC media player
    Version: 3.0.12
    Uninstall String: "C:\Program Files\VideoLAN\VLC\uninstall.exe"
    **********
  Step 2: -list "vlc" -u "C:\Program Files\VideoLAN\VLC\uninstall.exe"
  Step 3: Will get result back stating if the application has been uninstalled or not.
.EXAMPLE
  For a more complex uninstall of for example the Bentley CONNECTION Client with extra arguments.
  Step 1: -list "CONNECTION Client"
  Step 1 result:
    2 results 
    **********
    Name: CONNECTION Client
    Version: 11.0.3.14
    Silent Uninstall String: "C:\ProgramData\Package Cache\{54c12e19-d8a1-4c26-80cd-6af08f602d4f}\Setup_CONNECTIONClientx64_11.00.03.14.exe" /uninstall /quiet
    **********
    Name: CONNECTION Client
    Version: 11.00.03.14
    Uninstall String: MsiExec.exe /X{BF2011BD-2485-4CBA-BBFB-93205438C75B}
    **********
  Step 2: -list "CONNECTION Client" -u "C:\ProgramData\Package Cache\{54c12e19-d8a1-4c26-80cd-6af08f602d4f}\Setup_CONNECTIONClientx64_11.00.03.14.exe" -args "/uninstall /quiet"
  Step 3: Will get result back stating if the application has been uninstalled or not.
  .NOTES
  See https://github.com/subzdev/uninstall_software/blob/main/uninstall_software.ps1 . If you have extra additions please feel free to contribute and create PR
  v1.0 - 8/18/2021 Initial release
#>

[CmdletBinding()]
param(
    [switch]$list,
    [string]$find,
    [string]$u,
    [string]$args
)

$Paths = @("HKLM:\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\*", "HKLM:\SOFTWARE\\Wow6432node\\Microsoft\\Windows\\CurrentVersion\\Uninstall\*", "HKU:\*\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*")

$null = New-PSDrive -Name HKU -PSProvider Registry -Root Registry::HKEY_USERS

If ($list -And !($find) -And !($u) -And !($args)) {
    
    $ResultCount = (Get-ItemProperty $Paths | Where-Object { $_.UninstallString -notlike "" } | Measure-Object).Count
    Write-Output "$($ResultCount) results `r"
    Write-Output "********** `n"

    foreach ($app in Get-ItemProperty $Paths | Where-Object { $_.UninstallString -notlike "" } | Sort-Object DisplayName) {

        if ($app.UninstallString) {
            $UninstallString = if ($app.QuietUninstallString) { "Silent Uninstall String: $($app.QuietUninstallString)" } else { "Uninstall String: $($app.UninstallString)" }
            Write-Output "Name: $($app.DisplayName)"
            Write-Output "Version: $($app.DisplayVersion)"
            Write-Output $UninstallString
            Write-Output "`r"
            Write-Output "**********"
            Write-Output "`r"

        }
        else {
            
        }
    }
}

If ($list -And $find -And !($u)) {

    $FindResults = (Get-ItemProperty $Paths | Where-object { $_.Displayname -match [regex]::Escape($find) } | Measure-Object).Count
    Write-Output "`r"
    Write-Output "$($FindResults) results `r"
    Write-Output "********** `n"
    foreach ($app in Get-ItemProperty $Paths | Where-Object { $_.Displayname -match [regex]::Escape($find) } | Sort-Object DisplayName) {

        if ($app.UninstallString) {
            $UninstallString = if ($app.QuietUninstallString) { "Silent Uninstall String: $($app.QuietUninstallString)" } else { "Uninstall String: $($app.UninstallString)" }
            Write-Output "Name: $($app.DisplayName)"
            Write-Output "Version: $($app.DisplayVersion)"
            Write-Output $UninstallString
            Write-Output "`r"
            Write-Output "**********"
            Write-Output "`r"

        }
        else {
            
        }
    }
}


##################################
#uninstall code 32-bit and 64-bit
#################################
Function WithArgs ($u, $exeargs) {
    Start-Process -Filepath "$u" -ArgumentList $exeargs -Wait
    $UninstallTest = (Get-ItemProperty $Paths | Where-object { $_.UninstallString -match [regex]::Escape($u) }).DisplayName
    If ($UninstallTest) {
                    
        Write-Output "$($AppName) has not been uninstalled"

    }
    else {

        Write-Output "$($AppName) has been uninstalled"
    }
}

$AppName = (Get-ItemProperty $Paths | Where-object { $_.UninstallString -match [regex]::Escape($u) }).DisplayName

If ($list -And $find -And $u -Or $u -And !($list)) {

    If ($u -Match [regex]::Escape("MsiExec")) {

        $MsiArguments = $u -Replace "MsiExec.exe /I", "/X" -Replace "MsiExec.exe ", ""
        Start-Process -FilePath msiexec.exe -ArgumentList "$MsiArguments /quiet /norestart" -Wait
        $UninstallTest = (Get-ItemProperty $Paths | Where-object { $_.UninstallString -match [regex]::Escape($u) }).DisplayName
        If ($UninstallTest) {
                    
            Write-Output "$($AppName) has not been uninstalled"

        }
        else {

            Write-Output "$($AppName) has been uninstalled"
                
        }
    }
    else {
        If (Test-Path -Path "$u" -PathType Leaf) {
            If ($args) {

                $exeargs = $args + ' ' + "/S /SILENT /VERYSILENT /NORESTART"
                WithArgs $u $exeargs
            }
            else {

                $exeargs = "/S /SILENT /VERYSILENT /NORESTART"
                WithArgs $u $exeargs

            }

        }
        else {

            Write-Output "The path '$($u)' does not exist."

        }
    }
}

If ($list -And $u) {

    If ($u -Match [regex]::Escape("MsiExec")) {

        $MsiArguments = $u -Replace "MsiExec.exe /I", "/X" -Replace "MsiExec.exe ", ""
        Start-Process -FilePath msiexec.exe -ArgumentList "$MsiArguments /quiet /norestart" -Wait
        $UninstallTest = (Get-ItemProperty $Paths | Where-object { $_.UninstallString -match [regex]::Escape($u) }).DisplayName
        If ($UninstallTest) {
                    
            Write-Output "$($AppName) has not been uninstalled"

        }
        else {

            Write-Output "$($AppName) has been uninstalled"
        }

    }
    else {
        If (Test-Path -Path "$u" -PathType Leaf) {
            If ($args) {

                $exeargs = $args + ' ' + "/S /SILENT /VERYSILENT /NORESTART"
                WithArgs $u $exeargs
            }
            else {

                $exeargs = "/S /SILENT /VERYSILENT /NORESTART"
                WithArgs $u $exeargs

            }

        }
        else {

            Write-Output "The path '$($u)' does not exist."

        }
    }
}