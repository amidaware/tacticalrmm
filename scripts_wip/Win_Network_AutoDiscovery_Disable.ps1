# SET NETWORK DISCOVERY TO FALSE ON ALL CONNECTIONS

Get-NetFirewallRule -DisplayGroup 'Network Discovery'|Set-NetFirewallRule -Profile 'Private, Domain' -Enabled false -PassThru|select Name,DisplayName,Enabled,Profile|ft -a
