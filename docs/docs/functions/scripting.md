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

## Community Script

These are script that are built into Tactical RMM. They are provided and mantained by the Tactical RMM community. These scripts are updated whenever Tactical RMM is updated and can't be modified or deleted in the dashboard.

### Hiding Community Scripts
You can choose to hide community script throughout the dashboard by opening **Script Manager** and clicking the **Show/Hide Community Scripts** toggle button.

## Using Scripts

### Manual run on agent

In the **Agent Table**, you can right-click on an agent and select **Run Script**. You have the options of:
    - **Wait for Output** - Runs the script and waits for the script to finish running and displays the output.
    - **Fire and Forget** - Starts the script and does not wait for output.
    - **Email Output** - Starts the script and will email the output. Allows for using the default email address in the global settings or adding a new email address.

There is also an option on the agent context menu called **Run Favorited Script**. This will essentially Fire and Forget the script with default args and timeout.

### Bulk Run on agents

Tactical RMM offers a way to run a script on multiple agents at once. Browse to **Tools > Bulk Script** and select the target for the script to run.

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
