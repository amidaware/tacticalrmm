# Takes a long time to run. Probably needs at 5mins. 
# Want to add logon events too

$events = Get-WinEvent -Path C:\Windows\System32\winevt\Logs\Security.evtx | where { ($_.Id -eq 4624 -and $_.properties[8].value -eq 10) -or ($_.Id -eq 4634 -and $_.properties[4].value -eq 2) } 
    
foreach ($event in $events) {

    # userid will vary depending on event type:
    if ($event.Id -eq 4624) { $userid = $event.properties[5].value }
    if ($event.Id -eq 4634) { $userid = $event.properties[1].value }

    $event | Select TimeCReated, TaskDisplayName, Machinename, @{"Name" = "UserID"; "Expression" = { $userid } }
}