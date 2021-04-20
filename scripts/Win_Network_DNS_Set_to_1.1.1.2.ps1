# Cloudflare Family DNS see https://blog.cloudflare.com/introducing-1-1-1-1-for-families/

$ErrorActionPreference = 'SilentlyContinue'

if ((Get-WmiObject -Class Win32_ComputerSystem).PartOfDomain){
    write-host "Domain member, we better not update the DNS!!"
    exit
}
 
$PrimaryDNS = '1.1.1.2'
$SecondaryDNS = '1.0.0.2'
 
$DNSServers = $PrimaryDNS,$SecondaryDNS
 
$NICs = Get-WMIObject Win32_NetworkAdapterConfiguration | where{$_.IPEnabled -eq "TRUE"}
 
function get-return-status {
	Param ($code)
	If ($code -eq 0) {
		return "Success."
  } elseif ($code -eq 1) {
		return "Success, but Restart Required."
  } else {
		return "Error with Code $($code)!"
  }
}
 
Foreach($NIC in $NICs) {
  ""
  "-------"
  "Attempting to modify DNS Servers for the following NIC:"
  $NIC
  $returnValue = $NIC.SetDNSServerSearchOrder($DNSServers).ReturnValue
  $response = get-return-status($returnValue)
  Write-Host "Setting DNS Servers to ${$NICs}...$($response)"
  $returnValue = $NIC.SetDynamicDNSRegistration("True").ReturnValue
  $response = get-return-status($returnValue)
  Write-Host "Setting Dynamic DNS Registration to True...$($response)"
}