# Custom Fields

!!!info 
    v0.5.0 adds support for custom fields to be used in the dashboard and in scripts.

#### Adding Custom Fields

In the dashboard, go to **Settings > Global Settings > Custom Fields** and click **Add Custom Field**.

!!!info
    Everything between {{}} is CaSe sEnSiTive

The following options are available to configure on custom fields:

- **Model** - This is the object that the custom field will be added to. The available options are:
    - Agent
    - Site
    - Client
- **Name** - Sets the name of the custom field. This will be used to identify the custom field in the dashboard and in scripts.
- **Field Type** - Sets the type of field. Below are the allowed types.
    - Text
    - Number
    - Single select dropdown
    - Multi-select dropdown
    - Checkbox
    - DateTime
- **Input Options** - *Only available on Single and Multiple-select dropdowns*. Sets the options to choose from.
- **Default Value** - If no value is found when looking up the custom field; this value will instead be supplied.
- **Required** - This makes the field required when adding new Clients, Sites, and Agents. *If this is set a default value will need to be set as well*
- **Hide in Dashboard** - This will not show the custom field in Client, Site, and Agent forms in the dashboard. This is useful if the custom field's value is updated by a collector task and only supplied to scripts.

#### Using Custom Fields in the Dashboard

Once the custom fields are added, they will show up in the Client, Site, and Agent Add/Edit forms.

#### Using Custom Fields in Scripts

Tactical RMM allows for passing various database fields for Clients, Sites, and Agents in scripts. This includes custom fields as well! 

!!!warning
    The characters within the brackets is case-sensitive!

In your script's arguments, use the notation `{{client.AV_KEY}}`. This will lookup the client for the agent that the script is running on and find the custom field named `AV_KEY` and replace that with the value.

The same is also true for `{{site.no_patching}}` and `{{agent.Another Field}}`

For more information see SCRIPTING PAGE

#### Populating Custom Fields automatically

Tactical RMM supports automatically collecting information and saving them directly to custom fields. This is made possible by creating **Collector Tasks**. These are just normal Automated Tasks, but instead they will save the last line of the standard output to the custom field that is selected.

!!!info
    To populate a multiple select custom field, return a string with the options separated by a comma `"This,will,be,an,array"`

For more information See [Collector Tasks](automated_tasks.md#Collector Tasks)
