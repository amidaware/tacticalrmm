#Needs updating to include date
#Needs System Restore Size adjusting (50GB or 20% disk space)


Checkpoint-Computer -Description "Weekly Maintanence" -RestorePointType "MODIFY_SETTINGS"
Write-Host "System Restore Point created successfully"