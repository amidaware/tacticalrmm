<#
.SYNOPSIS
Script that will do the ICMPv4 ping and write to file with timestamps for logging.
.DESCRIPTION
This script will ping the specified host/IP with time stamps. The result will also be written to the log <Destination_PingOutput.txt> file.

Example usage:
.\Smart_Ping.ps1 -ComputerName myServer1 -min 10
This will ping the myServer1 for 10 minutes.

Author: phyoepaing3.142@gmail.com
Country: Myanmar(Burma)
Released: 12/13/2016

.EXAMPLE
.\Smart_Ping.ps1 -ComputerName myServer1 -hr 1 -min 20
This will ping  myServer1 for 1 hour and 20 minutes. Buffer size will be 32 bytes by default.

.\Smart_Ping.ps1 192.168.43.1 -size 5000
This will ping 192.168.43.1  10 minutes or 600 seconds by defaut. Buffer size will be 5000 bytes.

.PARAMETER hr
Specify the number of hours to ping a specified host. Decimal number is supported. Eg. -hr 0.5 for 30 minutes.

.PARAMETER min
Specify the number of minutes to ping a specified host. Decimal number is supported. Eg. -hr 0.5 for 30 seconds.

.PARAMETER sec
Specify the number of minutes to ping a specified host.

.LINK
You can find this script and more at: https://www.sysadminplus.blogspot.com/
#>

param([Parameter(Position = 0, Mandatory = $true)][string]$ComputerName, [single]$hr = 0, [single]$min = 0, $sec = 0, [int]$size = 32)

If ($size -gt 65500) { Write-Host -Fore red "Invalid buffer size specified. Valid range is from 0 to 65500."; Exit; }	## If the buffer size is larger than 65500, then exits the script.
If ($hr -eq 0 -AND $min -eq 0 -AND $sec -eq 0) { $min = 10 }
[int]$second = ($hr) * 3600 + $min * 60	+ $sec	## Convert Hour/Minute/Second value to seconds
$ts = [timespan]::fromseconds($second)					## Covert second values to h:m:ss
$var1 = "Duration of Ping time is $($ts.ToString("hh\:mm\:ss"))"
$var2 = "Ping from $($env:ComputerName) to $ComputerName at $([datetime]::now)";
Write-Host -fore yellow $var1;
Write-Host -fore yellow $var2;
$var1 | Out-File "$($ComputerName)_PingOutput.txt"; $var2  | Out-File -Append "$($ComputerName)_PingOutput.txt";
$Time = @(); ## Create the array to put the time values at each ping
############## Ping the specific host and manipulate output #################
Ping -t $ComputerName -n $second -l $size  | where { !($_ -match "ping" -OR $_ -Match "packets" -OR $_ -Match "Approximate" -OR $_ -Match "Minimum" -OR $_ -eq "") } | foreach {
	If ($_ -match "reply") { "$(([datetime]::now) ) $_" } else { "$(([datetime]::now) ) $_" } 
	$TimePiece = $_.Split(' ') -match "time"
	############## Fetch the ping packet round trip time and place into the variable   #########
	If ($TimePiece -match "<") {
		$Time += $TimePiece.split('<')[1].trimEnd('ms')
	} 
	elseif ($TimePiece -match '=') {
		$Time += $TimePiece.split('=')[1].trimEnd('ms')
	}
} | Tee-Object -Append "$($ComputerName)_PingOutput.txt"  
############# Calculate the the manimum, maximum & avarage ######################
$LastLine = "Maximum = $(($Time | measure -maximum).maximum)ms, Minimum = $(($Time | measure -minimum).minimum)ms, Average = $([int]($Time | measure -average).average)ms"
$LastLine | Out-File -Append "$($ComputerName)_PingOutput.txt"  
Write-Host -fore yellow $LastLine
