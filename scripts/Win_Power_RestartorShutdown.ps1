# This script will force restart computer. Add command paramter: shutdown to shutdown instead
# Normal restart doesn't install updates before issuing

$param1 = $args[0]

if ($param1 -eq 'shutdown') {
    Stop-Computer -ComputerName $env:COMPUTERNAME -Force
}
else {
    Restart-Computer -ComputerName $env:COMPUTERNAME -Force 
}