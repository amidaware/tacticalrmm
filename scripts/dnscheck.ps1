## names of hostname to run DNS checks against please leave the name in brackets
$hostname = 'bbc.com'

## allowed time for DNS check to be done (Milliseconds)
$time = 100

write-Output -NoNewLine "Verifying" $hostname " ... "

## Do a ping test to ensure hostname can be contacted

if (Test-Connection $hostname -Count 1 -ErrorAction SilentlyContinue) 
	{ 
	write-Output "Ping test passed for $hostname"
	} 
else 
	{
	write-Output "Ping Test Failed for $hostname" 
	exit 1
	}
	
## Test if the DNS record exists or not

try
	{  
	$dnscheck = [System.Net.DNS]::GetHostByName($hostname)
	$test = $true
	}  
catch
	{
	Write-Output "Unable to resolve DNS for $hostname"
	exit 1
	}
	
## Do some verification if DNS record exists

if($test)
	{

## Check time taken in Milliseconds to resolve hostname

	$start_time = Get-Date 
	nslookup $hostname
	$timetaken = $((Get-Date).Subtract($start_time).Milliseconds)
	Write-Output "Time taken: $timetaken Milliseconds"
if ($timetaken -ge $time) 
	{
	write-Output "DNS lookup for $hostname took longer than $time Milliseconds"
	exit 1
	}
	else 
	{ 
	Write-Output "Everything appears fine with your DNS for $hostname" 
	exit 0
	}
	}


Exit $LASTEXITCODE
