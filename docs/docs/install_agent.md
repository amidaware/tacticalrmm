# Installing an agent

!!!warning
    If you don't want to deal with AV flagging/deleting your agents, check the instructions for getting [code signed agents](code_signing.md)<br/><br />
    You must add antivirus exlusions for the tactical agent.<br/>
    Any decent AV will flag the agent as a virus, since it technically is one due to the nature of this software.<br/>
    Adding the following exlucions will make sure everything works, including agent update:<br/>
    `C:\Program Files\TacticalAgent\*`<br/>
    `C:\Program Files\Mesh Agent\*`<br/>
    `C:\Windows\Temp\winagent-v*.exe`<br/>
    `C:\Windows\Temp\trmm\*`<br/>
    `C:\temp\tacticalrmm*.exe`<br/>

## Dynamically generated executable

The generated exe is simply a wrapper around the Manual install method, using a single exe/command without the need to pass any command line flags to the installer.
All it does is download the generic installer from the agent's github [release page](https://github.com/wh1te909/rmmagent/releases) and call it using predefined command line args that you choose from the web UI.
It "bakes" the command line args into the executable.

From the UI, click **Agents > Install Agent**

You can also **right click on a site > Install Agent**. This will automatically fill in the client/site dropdown for you.

![siteagentinstall](images/siteagentinstall.png)

## Powershell

The powershell method is very similar to the generated exe in that it simply downloads the installer from github and calls the exe for you.

## Manual

The manual installation method requires you to first download the generic installer and call it using command line args.
This is useful for scripting the installation using Group Policy or some other batch deployment method.

!!!tip
    You can reuse the installer for any of the deployment methods, you don't need to constantly create a new installer for each new agent.<br/>
    The installer will be valid for however long you specify the token expiry time when generating an agent.

## Using a deployment link

Creating a deployment link is the recommended way to deploy agents.
The main benefit of this method is that the exectuable is generated only whenever the deployment download link is accessed, whereas with the other methods it's generated right away and the agent's version hardcoded into the exe.
Using a deployment link will allow you to not worry about installing using an older version of an agent, which will fail to install if you have updated your RMM to a version that is not compatible with an older installer you might have lying around.

To create a deployment, from the web UI click **Agents > Manage Deployments**.
![managedeployments](images/managedeployments.png)

!!!tip
    Create a client/site named "Default" and create a deployment for it with a very long expiry to have a generic installer that can be deployed anytime at any client/site.
    You can then move the agent into the correct client/site from the web UI after it's been installed.

Copy/paste the download link from the deployment into your browser. It will take a few seconds to dynamically generate the executable and then your browser will automatically download the exe.

## Optional installer args

The following optional arguments can be passed to any of the installation method executables:

```text
-log debug
```

Will print very verbose logging during agent install. Useful for troubleshooting agent install.

```text
-silent
```

This will not popup any message boxes during install, either any error messages or the "Installation was successfull" message box that pops up at the end of a successfull install.

```text
-proxy "http://proxyserver:port"
```

Use a http proxy

```text
-meshdir "C:\Program Files\Your Company Name\Mesh Agent"
```

Specify the full path to the directory containing `MeshAgent.exe` if using custom agent branding for your MeshCentral instance.

```text
-nomesh
```

Do not install meshcentral agent during tactical agent install. Note: take control, remote terminal and file browser will not work.

## Scripting Agent Installation

If you want to deploy the TRMM agent using AD, intune, mesh, teamviewer, Group Policy GPO etc this is a sample CMD script for deploying Tactical.

!!!note
    You will need to replace `deployment url` with your custom deployment URL

```bat
@echo off

REM Setup deployment URL
set "DeploymentURL="

set "Name="
for /f "usebackq tokens=* delims=" %%# in (
    `wmic service where "name like 'tacticalagent'" get Name /Format:Value`
) do (
    for /f "tokens=* delims=" %%g in ("%%#") do set "%%g"
)

if not defined Name (
    echo Tactical RMM not found, installing now.
    if not exist C:\TEMP\TRMM md C:\TEMP\TRMM
    powershell Set-ExecutionPolicy -ExecutionPolicy Unrestricted
    powershell Add-MpPreference -ExclusionPath C:\TEMP\TRMM
    powershell Add-MpPreference -ExclusionPath "C:\Program Files\TacticalAgent\*"
    powershell Add-MpPreference -ExclusionPath C:\Windows\Temp\winagent-v*.exe
    powershell Add-MpPreference -ExclusionPath "C:\Program Files\Mesh Agent\*"
    powershell Add-MpPreference -ExclusionPath C:\Windows\Temp\TRMM\*
    cd c:\temp\trmm
    powershell Invoke-WebRequest "%DeploymentURL%" -Outfile tactical.exe
    REM"C:\Program Files\TacticalAgent\unins000.exe" /VERYSILENT /SUPPRESSMSGBOXES /FORCECLOSEAPPLICATIONS
    tactical.exe
    powershell Remove-MpPreference -ExclusionPath C:\TEMP\TRMM
    rem exit /b 1
) else (
       echo Tactical RMM already installed Exiting
  Exit 0
)
```

There is also a full powershell version [here](https://wh1te909.github.io/tacticalrmm/3rdparty_screenconnect/#install-tactical-rmm-via-screeconnect-commands-window)

## Script for full agent uninstall

You can always use this to silently uninstall agent on workstations

```cmd
"C:\Program Files\TacticalAgent\unins000.exe" /VERYSILENT /SUPPRESSMSGBOXES /FORCECLOSEAPPLICATIONS
```
