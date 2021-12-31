# Scripting

Tactical RMM supports uploading existing scripts or adding new scripts right in the dashboard. Languages supported are:

- Powershell
- Windows Batch
- Python

## Adding Scripts
In the dashboard, browse to **Settings > Scripts Manager**. Click the **New** button and select either Upload Script or New Script. The available options for scripts are:

- **Name** - This identifies the script in the dashboard
- **Description** - Optional description for the script
- **Category** - Optional way to group similar scripts together. 
- **Type** - This sets the language of the script. Available options are:
    - Powershell
    - Windows Batch
    - Python
- **Script Arguments** - Optional way to set default arguments for scripts. These will autopopulate when running scripts and can be changed at runtime.
- **Default Timeout** - Sets the default timeout of the script and will stop script execution if the duration surpasses the configured timeout. Can be changed at script runtime
- **Favorite** - Favorites the script.

## Downloading Scripts

To download a Tactical RMM Script, click on the script in the Script Manager to select it. Then click the **Download Script** button on the top. You can also right-click on the script and select download

## Community Scripts

These are script that are built into Tactical RMM. They are provided and mantained by the Tactical RMM community. These scripts are updated whenever Tactical RMM is updated and can't be modified or deleted in the dashboard.

### Hiding Community Scripts
You can choose to hide community script throughout the dashboard by opening **Script Manager** and clicking the **Show/Hide Community Scripts** toggle button.

## Using Scripts

### Manual run on agent

In the **Agent Table**, you can right-click on an agent and select **Run Script**. You have the options of:

- **Wait for Output** - Runs the script and waits for the script to finish running and displays the output.
- **Fire and Forget** - Starts the script and does not wait for output.
- **Email Output** - Starts the script and will email the output. Allows for using the default email address in the global settings or adding a new email address.
- **Save as Note** - Saves the output as a Note that can be views in the agent Notes tab
- **Collector** - Saves to output to the specified custom field.

There is also an option on the agent context menu called **Run Favorited Script**. This will essentially Fire and Forget the script with default args and timeout.

### Script Arguments

The `Script Arguments` field should be pre-filled with information for any script that can accept or requires parameters.

<p style="background-color:#1e1e1e;">
&nbsp;<span style=color:#d4d4d4><</span><span style="color:#358cd6">Required Parameter Name</span><span style=color:#d4d4d4>></span> <span style=color:#d4d4d4><</span><span style="color:#358cd6">string</span><span style=color:#d4d4d4>></span><br>
&nbsp;<span style="color:#ffd70a">[</span><span style=color:#d4d4d4>-<</span><span style="color:#358cd6">Optional Parameter Name</span><span style=color:#d4d4d4>></span> <span style=color:#d4d4d4><</span><span style="color:#358cd6">string</span><span style=color:#d4d4d4>></span><span style="color:#ffd70a">]</span><br>
&nbsp;<span style="color:#ffd70a">[</span><span style=color:#d4d4d4>-<</span><span style="color:#358cd6">string</span><span style=color:#d4d4d4>></span> <span style="color:#c586b6">{</span><span style=color:#87cefa>(</span><span style=color:#d4d4d4><</span><span style="color:#358cd6">default string if not specified</span><span style=color:#d4d4d4>></span><span style=color:#87cefa>)</span> <span style=color:#d4d4d4>|</span> <span style=color:#d4d4d4><</span><span style="color:#358cd6">string2</span><span style=color:#d4d4d4>></span> <span style=color:#d4d4d4>|</span> <span style=color:#d4d4d4><</span><span style="color:#358cd6">string3</span><span style=color:#d4d4d4>></span><span style="color:#c586b6">}</span><span style="color:#ffd70a">]</span></p>

Where `[]` indicates an optional parameter

and `{}` indicates a parameter with several preconfigured parameter

and `()` indicates a default parameter if none is specified

### Bulk Run on agents

There is also an option on the agent context menu called **Run Favorited Script**.

### Automated Tasks

Tactical RMM allows scheduling tasks to run on agents. This leverages the Windows Task Scheduler and has the same scheduling options.

See [Automated Tasks](automated_tasks.md) for configuring automated tasks

### Script Checks

Scripts can also be run periodically on an agent and trigger an alert if it fails.

### Alert Failure/Resolve Actions

Scripts can be triggered when an alert is triggered and resolved. This script will run on any online agent and supports passing the alert information as arguments. 

For configuring **Alert Templates**, see [Alerting](./alerting.md)

See below for populating dashboard data in scripts and the available options.

## Using dashboard data in scripts

Tactical RMM allows passing in dashboard data to scripts as arguments. The below powershell arguments will get the client name of the agent and also the agent's public IP address

```
-ClientName {{client.name}} -PublicIP {{agent.public_ip}}
```

!!!info
    Everything between {{}} is CaSe sEnSiTive

See a full list of available options [Here](../script_variables.md)

### Getting Custom Field values

Tactical RMM supports pulling data from custom fields using the {{model.custom_field_name}} syntax.

See [Using Custom Fields in Scripts](custom_fields.md#Using Custom Fields in Scripts)

### Getting values from the Global Keystore

Tactical RMM supports getting values from the global key store using the {{global.key_name}} syntax

See [Global Keystore](keystore.md).

### Example Powershell Script

The below script takes five named values. The arguments will look like this: `-SiteName {{site.name}} -ClientName {{client.name}} -PublicIP {{agent.public_ip}} -CustomField {{client.AV_KEY}} -Global {{global.API_KEY}}`

```powershell
param (
   [string] $SiteName,
   [string] $ClientName,
   [string] $PublicIp,
   [string] $CustomField,
   [string] $Global
)

Write-Output "Site: $SiteName"
Write-Output "Client: $ClientName"
Write-Output "Public IP: $PublicIp"
Write-Output "Custom Fields: $CustomField"
Write-Output "Global: $Global"
```

## Script Snippets

Script Snippets allow you to create common code blocks or comments and apply them to all of your scripts. This could be initialization code, common error checking, or even code comments. 

### Adding Script Snippets

In the dashboard, browse to **Settings > Scripts Manager**. Click the **Script Snippets** button.

- **Name** - This identifies the script snippet in the dashboard
- **Description** - Optional description for the script snippet
- **Shell** - This sets the language of the script. Available options are:
    - Powershell
    - Windows Batch
    - Python

### Using Script Snippets

When editing a script, you can add template tags to the script body that contains the script snippet name. For example, if a script snippet exists with the name "Check WMF", you would put {{Check WMF}} in the script body and the snippet code will be replaced.

!!!info
    Everything between {{}} is CaSe sEnSiTive

The template tags will only be visible when Editing the script. When downloading or viewing the script code the template tags will be replaced with the script snippet code.

### Temporary Script location 

The script gets saved to a randomly created file in `c:\windows\temp\trmm\` and is then removed after execution or timeout.
