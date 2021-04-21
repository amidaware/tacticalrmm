# This script will force the computer to finish installing updates
# and restart. Normal restart doesn't install updates before issuing
# a reboot command. This one does.

$param1 = $args[0]

Restart-Computer -ComputerName $env:COMPUTERNAME -Force 

if ($param1 -eq 'shutdown') {
    Stop-Computer -ComputerName $env:COMPUTERNAME -Force
}