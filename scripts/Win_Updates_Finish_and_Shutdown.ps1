# This script will force the computer to finish installing updates
# and shutdown. Normal shutdown doesn't install updates before issuing
# a shutdown command. This one does.

Stop-Computer -ComputerName $env:COMPUTERNAME -Force