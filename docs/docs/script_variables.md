# Script Variables

Tactical RMM allows passing dashboard data into script as arguments. This uses the syntax `{{client.name}}`.

See below for the available options.

## Agent

- **{{agent.version}}** - Tactical RMM agent version
- **{{agent.operating_system}}** - Agent operating system example: *Windows 10 Pro, 64 bit (build 19042.928)*
- **{{agent.plat}}** - Will show the platform example: *windows*
- **{{agent.hostname}}** - The hostname of the agent
- **{{agent.public_ip}}** - Public IP address of agent
- **{{agent.total_ram}}** - Total RAM on agent. Returns an integer - example: *16* 
- **{{agent.boot_time}}** - Uptime of agent. Returns unix timestamp. example: *1619439603.0*
- **{{agent.logged_in_user}}** - Username of logged in user
- **{{agent.monitoring_type}}** - Returns a string of *workstation* or *server*
- **{{agent.description}}** - Description of agent in dashboard
- **{{agent.mesh_node_id}}** - The mesh node id used for linking the tactical agent to mesh.
- **{{agent.choco_installed}}** - Boolean to see if Chocolatey is installed
- **{{agent.patches_last_installed}}** - The date that patches were last installed by Tactical RMM. 
- **{{agent.needs_reboot}}** - Returns true if the agent needs a reboot
- **{{agent.time_zone}}** - Returns timezone configured on agent
- **{{agent.maintenance_mode}}** - Returns true if agent is in maintenance mode

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
