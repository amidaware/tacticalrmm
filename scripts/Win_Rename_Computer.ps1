# Chanage the computer name in Windows
# v1.0 
# First Command Parameter will be new computer name
# Second Command Parameter if yes will auto-restart computer

if ($Args.Count -eq 0) {
  Write-Output "Computer name arg is required"
  exit 1
}

$param1=$args[0]
$ToRestartTypeYes=$args[1]

Rename-Computer -newname "$param1"

# Restart the computer for rename to take effect
if ($ToRestartTypeYes -eq 'yes') {
    Restart-Computer -Force
}
