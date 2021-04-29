# enabling WINrm ( usually needed for windows admin centre)
# recent update disable or stops Winrm in services
#Add's firewall event for Winrm

Enable-PSRemoting -Force

Set-NetFirewallRule -Name WINRM-HTTP-In-TCP -RemoteAddress Any


