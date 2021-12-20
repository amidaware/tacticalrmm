# gretsky https://discord.com/channels/736478043522072608/744281869499105290/890953042332094514

$ErrorActionPreference = "SilentlyContinue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$env:COMPUTERNAME

$install = $NULL
$serviceName = 'tacticalagent'
$rmmURI = 'https://INSTALL_SCRIPT_LOCATION/rmm.ps1'
$headers = @{
	'X-API-KEY'    = 'YOURAPIKEY'
	"Content-Type" = "application/json"
}

$Model = (Get-WmiObject -Class win32_computersystem -ComputerName localhost).model
if ($Model.toupper().contains('VIRTUAL') -Or ($Model.toupper().contains('PROLIANT')) -Or ($Model.toupper().contains('VMWARE'))) {
	Write-Output 'Serveur'
	$rmmURI = 'https://INSTALL_SCRIPT_LOCATION/rmm_server.ps1'
}

$ChkReg = Test-Path 'HKLM:\SOFTWARE\TacticalRMM\'
If ($ChkReg -eq $True) {
	$regrmm = Get-ItemProperty -Path HKLM:\SOFTWARE\TacticalRMM\
}
else {
	write-host "Installing, no registry entry"
	Invoke-Expression ((new-object System.Net.WebClient).DownloadString($rmmURI))
	Start-Sleep -s 60
}

Try {
	$rmmagents = Invoke-RestMethod -Method Patch -Headers $headers -uri "https://rmm-api.DOMAIN.COM/agents/listagents/"
}
Catch {
	write-host "RMM down ???"
	Start-Sleep -s 5
	exit 1
}

Foreach ($rmmagent in $rmmagents) {

	$hostname = $rmmagent.hostname
	$agent_id = $rmmagent.agent_id
	$agentpk = $rmmagent.id

	if ($hostname -eq $env:COMPUTERNAME) {

		if ($agent_id -eq $regrmm.agentid) {
			Write-Host 'Not Duplicate!'
			$install = "OK"
			Start-Sleep -s 5
		}
		else {
			write-host "delete" $agentpk			
			$body = "{`"pk`":$agentpk}"
			Invoke-RestMethod -Method DELETE -Headers $headers -body $body -uri "https://rmm-api.DOMAIN.COM/agents/uninstall/" 
			Start-Sleep -s 5
		}

	}
}

if ($install -eq $NULL) {

	If (Get-Service $serviceName -ErrorAction SilentlyContinue) {
		write-host ('Tactical RMM Is Already Installed')
		& 'C:\Program Files\TacticalAgent\unins000.exe' /VERYSILENT
		Start-Sleep -s 20	
	}
	Invoke-Expression ((new-object System.Net.WebClient).DownloadString($rmmURI))
	Start-Sleep -s 30
	exit 0

}

if ($install -eq "OK") {
	write-host "OK!"
	Start-Sleep -s 5
	exit 0
}