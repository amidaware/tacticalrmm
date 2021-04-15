#This script sets current network profile to Private

$net = get-netconnectionprofile;Set-NetConnectionProfile -Name $net.Name -NetworkCategory Private