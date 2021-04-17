# author: https://github.com/bradhawkins85
$api = 'apichange'
$clientid = 'clientchange'
$siteid = 'sitechange'
$agenttype = '"atypechange"'
$power = powerchange
$rdp = rdpchange
$ping = pingchange
$auth = "tokenchange"

$headers = New-Object "System.Collections.Generic.Dictionary[[String],[String]]"
$headers.Add("Content-Type", "application/json")
$headers.Add("Authorization", "token " + [string]::Format($auth))
$response = Invoke-RestMethod "$api/agents/getagentversions/" -Method 'GET' -Headers $headers
$agentversion = $response.versions
$innosetup = "winagent-v$agentversion.exe"
$downloadlink = "https://github.com/wh1te909/rmmagent/releases/download/v$agentversion/winagent-v$agentversion.exe"

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$serviceName = 'tacticalagent'
If (Get-Service $serviceName -ErrorAction SilentlyContinue) {
    write-host ('Tactical RMM Is Already Installed')
} Else {
    $OutPath = $env:TMP
    $output = $innosetup

    $installArgs = @('-m install --api ', "$api", '--client-id', $clientid, '--site-id', $siteid, '--agent-type', "$agenttype", '--auth', "$auth")

    if ($power) {
        $installArgs += "--power"
    }

    if ($rdp) {
        $installArgs += "--rdp"
    }

    if ($ping) {
        $installArgs += "--ping"
    }

    Try
    {
        $DefenderStatus = Get-MpComputerStatus | select  AntivirusEnabled
        if ($DefenderStatus -match "True") {
            Add-MpPreference -ExclusionPath 'C:\Program Files\TacticalAgent\*'
            Add-MpPreference -ExclusionPath 'C:\Windows\Temp\winagent-v*.exe'
            Add-MpPreference -ExclusionPath 'C:\Program Files\Mesh Agent\*'
            Add-MpPreference -ExclusionPath 'C:\Windows\Temp\trmm*\*'
        }
    }
    Catch {
        # pass
    }
    
    Try
    {  
        Invoke-WebRequest -Uri $downloadlink -OutFile $OutPath\$output
        Start-Process -FilePath $OutPath\$output -ArgumentList ('/VERYSILENT /SUPPRESSMSGBOXES') -Wait
        write-host ('Extracting...')
        Start-Sleep -s 5
        Start-Process -FilePath "C:\Program Files\TacticalAgent\tacticalrmm.exe" -ArgumentList $installArgs -Wait
        exit 0
    }
    Catch
    {
        $ErrorMessage = $_.Exception.Message
        $FailedItem = $_.Exception.ItemName
        Write-Error -Message "$ErrorMessage $FailedItem"
        exit 1
    }
    Finally
    {
        Remove-Item -Path $OutPath\$output
    }
}
