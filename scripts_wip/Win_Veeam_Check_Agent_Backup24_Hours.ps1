#
# Script name:	check_veeam_eventlogs.ps1
# Version: 		1.1
# Created on: 	6May2015
# Modified on:  24April2018
# Author: 		Dallas Haselhorst
# Purpose: 		Check Veeam Backup success or failure via event logs 
#				Note: this requires PowerShell, however, it does NOT use the Veeam PowerShell plug-in 
#
# Copyright:
#	This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published
#	by the Free Software Foundation, either version 3 of the License, or (at your option) any later version. This program is distributed 
#	in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A 
#	PARTICULAR PURPOSE. See the GNU General Public License for more details. You should have received a copy of the GNU General Public 
#	License along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Heavily modified from the original script watch-eventlogs.ps1 
#	written by Aaron Wurthmann (aaron (AT) wurthmann (DOT) com). Nonetheless, thanks Aaron!
#
#  Older versions of NCPA used the following format, i.e. the following line can be copied to the $ARG1$ text box.
#  -t '<token>' -P <port number> -M 'agent/plugin/check_veeam_eventlogs.ps1/<ArgBackupJobName>/<ArgLastHours>'
#  Newer versions of NCPA would use the following format. Note the removal of "agent" and the added "s" to plugin
#  -t '<token>' -P <port number> -M 'plugins/check_veeam_eventlogs.ps1/<ArgBackupJobName>/<ArgLastHours>'
#
#  For testing from the Nagios command line, add './check_ncpa.py -H <IP address>' to the above line
#	ArgBackupJobName is required. 
#       *** If your backup job name has special characters or spaces, I would suggest removing them! ***
#	ArgLastMinutes should be populated with the time to check in minutes, e.g. 60 (for 1 hour), 120 (for 2 hours), 
#
#  Old Example
#  -t 'TokenPass' -P 5693 -M 'agent/plugin/check_veeam_eventlogs.ps1/Management_VMs/24' 
#	-- above line would check the last 24 hours of Veeam Backup logs for the job named "Management_VMs"
#  New Example
#  -t 'TokenPass' -P 5693 -M 'plugins/check_veeam_eventlogs.ps1/TS01/24'
#	-- above line would check the last 24 hours of Veeam Backup logs for the job named "TS01"


# Pull in arguments
$ArgLogName = "Veeam Agent" # veeam backup event log
$ArgEntryType = 1,2,3,4 # look for critical, error, warning and informational logs
$ArgProviderName = "Veeam Agent"
$ArgEventID = 190 # backup job complete event id

$ArgBackupJobName = "Daily Backup"
$ArgLastHours = 24


if (!$ArgBackupJobName) { 
write-host "Sorry... at the very least, I need a backup job name."
write-host "Command line usage: check_veeam_eventlogs.ps1 <Job Name> <Last X Hours>" 
write-host "Nagios NCPA usage: agent/plugin/check_veeam_eventlogs.ps1/<Job Name>/<Last X Hours>" 
exit
}
# Setting default values if null 
if (!$ArgLastHours) { $ArgLastHours = (24) }
if (!$ArgWarningTH) { $ArgWarningTH = 0 }
if (!$ArgCriticalTH) { $ArgCriticalTH = 0 }
if (!$ArgMaxEntries) { $ArgMaxEntries = 50 }

$CriticalErrorResultCount = 0
$WarningResultCount = 0
$InfoResultCount = 0
$EventTypeLoopCount = 0
$LogNameLoopCount = 0
$ProviderNameLoopCount = 0
$EventIDLoopCount = 0

$Properties='Level','Message','ProviderName','TimeCreated','Id'

$Filter = @{
    LogName = $ArgLogName
    StartTime = (Get-Date).AddHours(-$ArgLastHours)
}

if($ArgProviderName) { $Filter += @{ProviderName = $ArgProviderName } }
if($ArgEventID) { $Filter += @{Id = $ArgEventID } }
if($ArgEntryType) { $Filter += @{Level = $ArgEntryType } }

# -ea SilentlyContinue gets rid of non-terminating error resulting from zero events
$LogEntries = Get-WinEvent -MaxEvents $ArgMaxEntries -FilterHashtable $Filter -ea SilentlyContinue -Oldest | Select-Object -Property $Properties 

if ($LogEntries) {

    ForEach ($LogEntry in $LogEntries) {
		if ($LogEntry.Message.ToString() -like "*Veeam Agent `'$ArgBackupJobName`'*")
		{
        $Level=$LogEntry.Level.ToString()
		if (($Level -eq 1) -Or ($Level -eq 2)) # find critical and errors
		{
		$Message=$LogEntry.Message.Substring(0,[System.Math]::Min(180, $LogEntry.Message.Length)).TrimEnd().ToString()
		$ProviderName=$LogEntry.ProviderName.ToString()
        $TimeCreated=$LogEntry.TimeCreated.ToString()
        $Id=$LogEntry.Id.ToString()
        $CriticalErrorResultCount++ 
         
                $CriticalErrorResults=@"
				
At: $TimeCreated
Level: $Level 
Event ID: $Id
Message: $Message
Source: $ProviderName
$CriticalErrorResults
"@
		}
		elseif ($Level -eq 3) # find warnings
		{
		$Message=$LogEntry.Message.Substring(0,[System.Math]::Min(180, $LogEntry.Message.Length)).TrimEnd().ToString()
		$ProviderName=$LogEntry.ProviderName.ToString()
        $TimeCreated=$LogEntry.TimeCreated.ToString()
        $Id=$LogEntry.Id.ToString()
        $WarningResultCount++ 
         
                $WarningResults=@"

At: $TimeCreated
Level: $Level 
Event ID: $Id
Message: $Message
Source: $ProviderName
$WarningResults
"@
		}
		else # all that's left, find info (4) messages
		{
		$Message=$LogEntry.Message.Substring(0,[System.Math]::Min(180, $LogEntry.Message.Length)).TrimEnd().ToString()
		$ProviderName=$LogEntry.ProviderName.ToString()
        $TimeCreated=$LogEntry.TimeCreated.ToString()
        $Id=$LogEntry.Id.ToString()
        $InfoResultCount++ 
         
                $InfoResults=@"
				
At: $TimeCreated
Level: $Level 
Event ID: $Id
Message: $Message
Source: $ProviderName
$InfoResults
"@
		}
    }

}

}

$Results= @"
$CriticalErrorResults $WarningResults $InfoResults
"@

if ($ArgEntryType) {
$TypeArray = @("all level","critical","error","warning","informational")
$LevelString = foreach ($Entry in $ArgEntryType) { 
	if ($ArgEntryType.Count -gt 1) { 
	$LevelStringBuild = $TypeArray[$Entry]
		if ($ArgEntryType.Count -ne $EventTypeLoopCount+1) {
		$LevelStringBuild +=","
		}
	}

	else { $LevelStringBuild = $TypeArray[$Entry] }
	$EventTypeLoopCount++
	$LevelStringBuild
	}
}

$LogNameString = foreach ($LogNameEntry in $ArgLogName) { 
	$LogNameStringBuild += $LogNameEntry
	if ($ArgLogName.Count -gt 1 -And $ArgLogName.Count -ne $LogNameLoopCount+1) {
		$LogNameStringBuild += ", "
		}
	$LogNameLoopCount++
	}

$ProviderNameString = foreach ($ProviderNameEntry in $ArgProviderName) { 
	$ProviderNameStringBuild += $ProviderNameEntry
	if ($ArgProviderName.Count -gt 1 -And $ArgProviderName.Count -ne $ProviderNameLoopCount+1) {
		$ProviderNameStringBuild += ", "
		}
	$ProviderNameLoopCount++
	}

$EventIDString = foreach ($EventIDEntry in $ArgEventID) { 
	$EventIDStringBuild += "$EventIDEntry"
	if ($ArgEventID.Count -gt 1 -And $ArgEventID.Count -ne $EventIDLoopCount+1) {
		$EventIDStringBuild += ", "
		}
	$EventIDLoopCount++
	}	

If ($CriticalErrorResultCount -gt 0) {
        $ResultString += "Backup failed: $CriticalErrorResultCount critical error(s) for backup job $ArgBackupJobName in last $ArgLastHours hours "
		$NagiosMetricString += "'Errors'=$CriticalErrorResultCount 'BackupUnknown'=1 "
		$ExitCode = 1
    }

If ($WarningResultCount -gt 0) {
        $ResultString += "Warning: backup job $ArgBackupJobName had $WarningResultCount warning message(s) in the last $ArgLastHours hours "
		If ($ExitCode -ne 1) {
		$NagiosMetricString += "'BackupUnknown'=1 "	
		$ExitCode = 1 
		}
		$NagiosMetricString += "'Warnings'=$WarningResultCount "
		
    }

If (($InfoResultCount -lt 1) -And ($ExitCode -ne 1)) {
        $ResultString += "Backup failed: backup job $ArgBackupJobName has not run in last $ArgLastHours hours "
		$NagiosMetricString += "'BackupNotRun'=1 "
		If ($ExitCode -ne 1) { $ExitCode = 1 }
    }
	
If (($InfoResultCount -ge 1) -And ($CriticalErrorResultCount -eq 0 ) -And ($WarningResultCount -eq 0 )){
        $ResultString += "OK: backup job $ArgBackupJobName completed successfully in last $ArgLastHours hours "
		$NagiosMetricString = "'BackupSuccess'=1 "
		$ExitCode = 0 
    }

	write-host $ResultString 
	write-host $Results 
	write-host $ResultString"|"$NagiosMetricString
	exit $ExitCode