# Script Variables

Tactical RMM allows passing dashboard data into script as arguments. This uses the syntax `{{client.name}}`.

See below for the available options.

!!!info
    Everything between {{}} is CaSe sEnSiTive

## Agent

- **{{agent.version}}** - Tactical RMM agent version
- **{{agent.operating_system}}** - Agent operating system example: *Windows 10 Pro, 64 bit (build 19042.928)*
- **{{agent.plat}}** - Will show the platform example: *windows*
- **{{agent.plat_release}}** - Will show the platform release
- **{{agent.hostname}}** - The hostname of the agent
- **{{agent.local_ip}}** - Local IP address of agent
- **{{agent.public_ip}}** - Public IP address of agent
- **{{agent.agent_id}}** - agent ID in database
- **{{agent.last_seen}}** - Date and Time Agent last seen
- **{{agent.used_ram}}** - Used RAM on agent. Returns an integer - example: *16* 
- **{{agent.total_ram}}** - Total RAM on agent. Returns an integer - example: *16* 
- **{{agent.boot_time}}** - Uptime of agent. Returns unix timestamp. example: *1619439603.0*
- **{{agent.logged_in_username}}** - Username of logged in user
- **{{agent.last_logged_in_user}}** - Username of last logged in user
- **{{agent.monitoring_type}}** - Returns a string of *workstation* or *server*
- **{{agent.description}}** - Description of agent in dashboard
- **{{agent.mesh_node_id}}** - The mesh node id used for linking the tactical agent to mesh.
- **{{agent.overdue_email_alert}}** - Returns true if overdue email alerts is enabled in TRMM
- **{{agent.overdue_text_alert}}** - Returns true if overdue SMS alerts is enabled in TRMM
- **{{agent.overdue_dashboard_alert}}** - Returns true if overdue agent alerts is enabled in TRMM
- **{{agent.offline_time}}** - Returns offline time setting for agent in TRMM
- **{{agent.overdue_time}}** - Returns overdue time setting for agent in TRMM
- **{{agent.check_interval}}** - Returns check interval time setting for agent in TRMM
- **{{agent.needs_reboot}}** - Returns true if reboot is pending on agent
- **{{agent.choco_installed}}** - Returns true if Chocolatey is installed
- **{{agent.patches_last_installed}}** - The date that patches were last installed by Tactical RMM. 
- **{{agent.needs_reboot}}** - Returns true if the agent needs a reboot
- **{{agent.time_zone}}** - Returns timezone configured on agent
- **{{agent.maintenance_mode}}** - Returns true if agent is in maintenance mode
- **{{agent.block_policy_inheritance}}** - Returns true if agent has block policy inheritance
- **{{agent.alert_template}** - Returns true if agent has block policy inheritance

## Client
- **{{client.name}}** - Returns name of client

## Site
- **{{site.name}}** - Returns name of Site

## Alert

!!!info
    Only available in failure and resolve actions on alert templates!
    
- **{{alert.alert_time}}** - Time of the alert
- **{{alert.message}}** - Alert message
- **{{alert.severity}}** - Severity of the alert *info, warning, or error*
