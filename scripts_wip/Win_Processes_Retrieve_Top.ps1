#Needs Command parameter updates


Get-WmiObject Win32_PerfFormattedData_PerfProc_Process | `  where-object{ $_.Name -ne "_Total" -and $_.Name -ne "Idle"} | `  Sort-Object PercentProcessorTime -Descending | ` select -First 5 | ` Format-Table Name,IDProcess,PercentProcessorTime -AutoSize