#  N-Able TAKE CONTROL

## N-Able Take Control Integration (Solarwinds/Beanywhere)

!!!info
     You can setup a full automation policy to collect the machine GUID but this example will collect from just one agent for testing purposes.

From the UI go to **Settings > Global Settings > CUSTOM FIELDS > Agents**

Add Custom Field</br>
**Target** = `Agent`</br>
**Name** = `TakeControlID`</br>
**Field Type** = `Text`</br>

While in Global Settings go to **URL ACTIONS**

Add a URL Action</br>
**Name** = `N-Able Take Control`</br>
**Description** = `Connect to a Take Control Session`</br>
**URL Pattern** =

```html
mspasp://{{agent.BeAnywhere}}
```
Add script with this name Take Control - Get TakeControlID for client:</br>
```
$ConfigPath = $Env:ProgramData + "\GetSupportService\BASupSrvc.ini"
$ResultsIdSearch = Select-String -Path $ConfigPath -Pattern ServerUniqueID
$Result = @($ResultsIdSearch -split '=')
$id = $Result[1]
$Text = "-s " + $id
$ENCODED = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Text))
Write-Output $ENCODED

```

Navigate to an agent with Take Control running (or apply using **Settings > Automation Manager**).</br>
Go to Tasks.</br>
Add Task</br>
**Select Script** = `Take Control - Get TakeControlID for client`</br>
**Descriptive name of task** = `Collects the TakeControlID.`</br>
**Collector Task** = `CHECKED`</br>
**Custom Field to update** = `TakeControlID`</br>

Click **Next**</br>
Add **Schedule**</br>
Click **Add Task**

Right click on the newly created task and click **Run Task Now**.

Give it a second to execute then right click the agent that you are working with and go to **Run URL Action > N-Able Take Control**

It launch the session in Take Control desktop Console.
