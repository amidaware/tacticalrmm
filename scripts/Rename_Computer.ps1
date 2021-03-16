# Chanage the computer name in Windows
# v1.0 
# First Command Parameter will be new computer name
# Second Command Parameter if yes will auto-restart computer

$param1=$args[0]
$ToRestartTypeYes=$args[1]

Rename-Computer -newname "$param1"

# Restart the computer for rename to take effect
if ($ToRestartTypeYes -eq 'yes') {
    Restart-Computer -Force
}