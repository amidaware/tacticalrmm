# Automation Policies

Automation policies in Tactical RMM allow for mass deployment of Checks, Automated Tasks, Patch Policies, and Alert Templates. You can apply Automation Policies to:

- Global Settings
- Client
- Site
- Agent

You can also see a list of Relations that show what policy is applied to what Clients | Sites | Agents
## Creating Automation Policies

In the dashboard, navigate to **Settings > Automation Manager**. Use the **Add** button to create a blank Automation Policy. The options available are:

- **Name** - The name that will be used to identify the automation policy in the dashboard
- **Description** - Optional description of the automation policy
- **Enabled** - Specifies if the automation policy is active or not
- **Enforced** - Specifies that the automation policy should overwrite any conflicting checks configured directly on the agent

## Policy Inheritance

They get applied in this order:

1. Global Settings
2. Client
3. Site
4. Agent
   
and at each level you can Block policy inheritance from the level above using checkboxes in the appropriate screens.

## Adding Windows Patch Management Policy

Under the Automation Manager you can create a Patch Policy and control what patches are applied, when, and if the computer is rebooted after.

!!!note
    Most "regular" Windows patches are listed in the "Other" category.
