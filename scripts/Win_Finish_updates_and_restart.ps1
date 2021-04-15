# This script will force the computer to finish installing updates
# and restart. Normal restart doesn't install updates before issuing
# a reboot command. This one does.

Restart-Computer -ComputerName $env:COMPUTERNAME -Force 
