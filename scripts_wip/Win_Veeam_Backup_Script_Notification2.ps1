# Untested probably doesn't work

$event = Get-EventLog "Veeam Backup" -newest 1 -After (Get-Date).AddDays(-1) | Where-Object { $_.EventID -eq 0 }

if ($event.entrytype -eq "Error") {
  write-host "We got an event that is an error from Veeam Backup!"
  Rmm-Alert -Category "veeam_backup_failed" -Body "Veeam Backup Failed on $(%computername%) - message: $($event.message)"
}
else {
  write-host "No errors here"
}
else {
  Write-Output "Veeam not Installed
  exit 0"
}


Exit $LASTEXITCODE