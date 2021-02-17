# Alerting Overview

## Notification Types

* *Email Alerts* - Sends email
* *SMS Alerts* - Sends text message
* *Dashboard Alerts* - Adds a notification in the dashboard alert icon


## Alert Severities

* Informational
* Warning
* Error

#### Agents
Agent offline alerts always have an error severity.

#### Checks
Checks can be configured to create alerts with different severities

* Memory and Cpuload checks can be configured with a warning and error threshold. To disable one of them put in a 0.
* Script checks allow for information and warning return codes. Everything else, besides a 0 will result in an error severity.
* Event Log, service, and ping checks require you to set the severity to information, warning, or error.

#### Automated Tasks
For automated tasks, you set the what the alert severity should be directly on the task.


## Configure Alert Templates
Alert template allow you to setup alerting and notifications on many agents at once. Alert templates can be applied to Sites, Client, Automation Policies, and in the Global Settings.

To create an alert template, go to Settings > Alerts Manager. Then click New

In the form, give the alert template a name and make sure it is enabled.

Optionally setup any of the below settings:
* *Failure Action* - Runs the selected script once on any agent. This is useful for running one-time tasks like sending an http request to an external system to create a ticket.
* *Failure action args* - Optionally pass in arguments to the failure script.
* *Failure action timeout* - Sets the timeout for the script.
* *Resolved action* - Runs the selected script once on any agent if the alert is resolved. This is useful for running onetime tasks like sending an http request to an external system to close the ticket that was created.
* *Resolved action args* - Optionally pass in arguments to the resolved script.
* *Resolved action timeout* - Sets the timeout for the script.
* *Email Recipients* - Overrides the default email recipients in Global Settings. 
* *From Email* - Overrides the From email address in Global Settings.
* *SMS Recipients* - Overrides the SMS recipients in Global Settings.
* *Include desktops* - Will apply to desktops
#### agent/check/task settings
* *Email on resolved* - Sends a email when the alert clears
* *Text on resolved* - Sends a text when the alert clears
* *Always email* - This enables the email notification setting on the agent/check/task
* *Always sms* - This enables the text notification setting on the agent/check/task
* *Always dashboard alert* - This enables the dashboard alert notification setting on the agent/check/task
* *Periodic notification* - This sets up a periodic notification on for the agent/check/task alert
* *Alert on severity* - When configured, will only send a notification through the corresponding channel if the alert is of the specified severity

## Applying Alert Templates

Alerts are applied in the following over. The agent picks the closest matching alert template.

* Right-click on any Client or Site and go to Assign Alert Template
* In Automation Manager, click on Assign Alert Template for the policy you want to apply it to
* In Global Settings, select the default alert template

1. Policy w/ Alert Template applied to Site
2. Site
3. Policy w/ Alert Template applied to Client
4. Client
5. Default Alert Template
