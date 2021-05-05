<#
Requires global variables for serviceName "ScreenConnectService" and url "ScreenConnectInstaller"'
serviceName is the name of the ScreenConnect Service once it is installed EG: "ScreenConnect Client (1327465grctq84yrtocq)"
url is the path the download the exe version of the ScreenConnect Access installer'
Both variables values must start and end with " (Prior to TRMM Version 0.6.5), remove / don't use " on TRMM Version 0.6.5 or later.
Also accepts uninstall variable to remove the installed instance if required. 
#>

param (
  [string] $serviceName,
  [string] $url,
  [string] $clientname,
  [string] $sitename,
  [string] $action
)

$clientname = $clientname.Replace(" ","%20")
$sitename = $sitename.Replace(" ","%20")
$url = $url.Replace("&t=&c=&c=&c=&c=&c=&c=&c=&c=","&t=&c=$clientname&c=$sitename&c=&c=&c=&c=&c=&c=")
$ErrorCount = 0

if (!$serviceName) {
    write-output "Variable not specified ScreenConnectService, please create a global custom field under Client called ScreenConnectService, Example Value: `"ScreenConnect Client (1327465grctq84yrtocq)`" `n"
    $ErrorCount += 1
}
if (!$url) {
    write-output "Variable not specified ScreenConnectInstaller, please create a global custom field under Client called ScreenConnectInstaller, Example Value: `"https://myinstance.screenconnect.com/Bin/ConnectWiseControl.ClientSetup.exe?h=stupidlylongurlhere`" `n"
    $ErrorCount += 1
}

if (!$ErrorCount -eq 0) {
exit 1
}

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
if ($action -eq "uninstall") {
        $MyApp = Get-WmiObject -Class Win32_Product | Where-Object{$_.Name -eq "$serviceName"}
        $MyApp.Uninstall()
} else {
    If (Get-Service $serviceName -ErrorAction SilentlyContinue) {

        If ((Get-Service $serviceName).Status -eq 'Running') {
            Try
            {
            Write-Output "Stopping $serviceName"
            Set-Service -Name $serviceName -Status stopped -StartupType disabled
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
                }

        } Else {

            Try
            {
            Write-Host "Starting $serviceName"
            Set-Service -Name $serviceName -Status running -StartupType automatic
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
                }

        }

    } Else {

        $OutPath = $env:TMP
        $output = "screenconnect.exe"

        Try
        {
			    $start_time = Get-Date
			    $wc = New-Object System.Net.WebClient
			    $wc.DownloadFile("$url&c=$company&c=$site", "$OutPath\$output")
            Start-Process -FilePath $OutPath\$output -Wait
			    Write-Output "Time taken to download and install: $((Get-Date).Subtract($start_time).Seconds) second(s)"
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
}
