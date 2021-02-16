# author: https://github.com/bradhawkins85
$api = '"apichange"'
$clientid = 'clientchange'
$siteid = 'sitechange'
$agenttype = '"atypechange"'
$power = powerchange
$rdp = rdpchange
$ping = pingchange
$auth = '"tokenchange"'

$serviceName = 'tacticalagent'
If (Get-Service $serviceName -ErrorAction SilentlyContinue) {
    write-host ('Tactical RMM Is Already Installed')
} Else {

	# Download latest wh1te909/rmmagent release from github

	$repo = "wh1te909/rmmagent"
	$releases = "https://api.github.com/repos/$repo/releases"

	Write-Host Determining latest release
	$tag = (Invoke-WebRequest $releases | ConvertFrom-Json)[0].tag_name
	$file = "winagent-$tag.exe"

	$downloadlink = "https://github.com/$repo/releases/download/$tag/$file"
	if ([Environment]::Is64BitOperatingSystem) {
		$innosetup = "$name-$tag.exe"
	} else {
		$innosetup = "$name-$tag-x86.exe"
	}

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
        Invoke-WebRequest -Uri $downloadlink -OutFile $OutPath\$output
        Start-Process -FilePath $OutPath\$output -ArgumentList ('/VERYSILENT /SUPPRESSMSGBOXES') -Wait
        write-host ('Extracting...')
        Start-Sleep -s 10
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
