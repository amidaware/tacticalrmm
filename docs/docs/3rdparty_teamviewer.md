# TeamViewer

## TeamViewer Integration

!!!info
     You can setup a full automation policy to collect the machine GUID but this example will collect from just one agent for testing purposes.

From the UI go to **Settings > Global Settings > CUSTOM FIELDS > Agents**

Add Custom Field</br>
**Target** = `Agent`</br>
**Name** = `TeamViewerClientID`</br>
**Field Type** = `Text`</br>

![Service Name](images/3rdparty_teamviewer1.png)

While in Global Settings go to **URL ACTIONS**

Add a URL Action</br>
**Name** = `TeamViewer Control`</br>
**Description** = `Connect to a Team Viewer Session`</br>
**URL Pattern** =

```html
https://start.teamviewer.com/device/{{agent.TeamViewerClientID}}/authorization/password/mode/control
```

Navigate to an agent with TeamViewer running (or apply using **Settings > Automation Manager**).</br>
Go to Tasks.</br>
Add Task</br>
**Select Script** = `TeamViewer - Get ClientID for client` (this is a builtin script from script library)</br>
**Descriptive name of task** = `Collects the ClientID for TeamViewer.`</br>
**Collector Task** = `CHECKED`</br>
**Custom Field to update** = `TeamViewerClientID`</br>

![Service Name](images/3rdparty_teamviewer2.png)

Click **Next**</br>
Check **Manual**</br>
Click **Add Task**

Right click on the newly created task and click **Run Task Now**.

Give it a second to execute then right click the agent that you are working with and go to **Run URL Action > TeamViewer Control**

It launch the session and possibly promt for password in TeamViewer.
