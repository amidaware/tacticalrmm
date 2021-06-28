# Connectwise Control Integration
!!!info
     To make this work you will need the name of a the Service from one of your agents running a Screen Connect Guest.

!!!info
     You can setup a full automation policy to collect the machine GUID but this example will collect from just one agent for testing purposes.

From the UI go to <b> Settings>Global Settings>CUSTOM FIELDS>Agents </b>

Add Custom Field</br>
<b>Target</b> = Client</br>
<b>Name</b> = ScreenConnectService</br>
<b>Field Type</b> = Text </br>
<b>Default Value</b> = The name of your SC Service ex. ScreenConnect Client (XXXXXXXXXXXXXXXXX)</br>

Add Custom Field</br>
<b>Target</b> = Agent</br>
<b>Name</b> = ScreenConnectGUID</br>
<b>Field Type</b> = Text</br>

While in Global Settings go to <b> URL ACTIONS </b>

Add a URL Action</br>
<b>Name</b> = ScreenConnect</br>
<b>Description</b> = Launch Screen Connect Session</br>
<b>URL Pattern</b> = https://your_screenconnect_fqdn_with_port/Host#Access/All%20Machines//{agent.ScreenConnectGuid}}/Join

Navigate to an agent with ConnectWise Service running.</br>
Go to Tasks.</br>
Add Task</br>
<b>Select Script</b> = ScreenConnect - Get GUID for client  (this is a built in script)</br>
<b>Script argument</b> = -serviceName{{client.ScreenConnectService}}</br>
<b>Descriptive name of task</b> = Collects the Machine GUID for ScreenConnect.</br>
<b>Collector Task</b> = CHECKED</br>
<b>Custom Field to update</b> = ScreenConectGUID</br>

Click <b>Next</b></br>
Check <b>Manual</b></br>
Click <b>Add Task</b>

Right click on the newly created task and click <b> Run Task Now</b>.

Give it a second to execute then right click the agent that you are working with and go to <b> Run URL Action>ScreenConnect</b>

It should ask you to sign into your Connectwise Control server if you are not already logged in and launch the session.

