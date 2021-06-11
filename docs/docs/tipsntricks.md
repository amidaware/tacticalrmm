# Tips and Tricks

## Customize User Interface

Top right click Username, look at preferences pane. Set default tab: Servers|Workstations|Mixed

![User Preferences](images/trmm_user_preferences.png)

*****

## Screenconnect / Connectwise Control

### Install Tactical RMM via Screeconnect commands window

1. Create a Deplopment under Agents | Manage Deployments
2. Replace `<deployment URL>` below with your Deployment Download Link.

**x64**

```cmd
#!ps
#maxlength=500000
#timeout=600000

Invoke-WebRequest "<deployment URL>" -OutFile ( New-Item -Path "C:\temp\trmminstallx64.exe" -Force )
$proc = Start-Process c:\temp\trmminstallx64.exe -ArgumentList '-silent' -PassThru
Wait-Process -InputObject $proc

if ($proc.ExitCode -ne 0) {
    Write-Warning "$_ exited with status code $($proc.ExitCode)"
}
Remove-Item -Path "c:\temp\trmminstallx64.exe" -Force 
```

**x86**

```cmd
#!ps
#maxlength=500000
#timeout=600000

Invoke-WebRequest "<deployment URL>" -OutFile ( New-Item -Path "C:\temp\trmminstallx86.exe" -Force )
$proc = Start-Process c:\temp\trmminstallx86.exe -ArgumentList '-silent' -PassThru
Wait-Process -InputObject $proc

if ($proc.ExitCode -ne 0) {
    Write-Warning "$_ exited with status code $($proc.ExitCode)"
}
Remove-Item -Path "c:\temp\trmminstallx86.exe" -Force 
```

### 
