<#
Requires global variables for serviceName "ScreenConnectService" 
serviceName is the name of the ScreenConnect Service once it is installed EG: "ScreenConnect Client (1327465grctq84yrtocq)"
Variable value must start and end with " (Prior to TRMM Version 0.6.5), remove / don't use " on TRMM Version 0.6.5 or later.
Requires Custom Fields Agent entry Name: ScreenConnectGUID   Type: text
URL Action entry (check your screenconnect to see what folder name is your "All Machines" folder): https://YOURNAME.screenconnect.com/Host#Access/All%20Machines//{{agent.ScreenConnectGUID}}/Join
    or https://YOURNAME.screenconnect.com/Host#Access/All%20Machines%20by%20Company//{{agent.ScreenConnectGUID}}/Join
#>

param (
    [string] $serviceName
)

if (!$serviceName) {
    write-output "Variable not specified ScreenConnectService, please create a global custom field under Client called ScreenConnectService, Example Value: `"ScreenConnect Client (1327465grctq84yrtocq)`" `n"
    $ErrorCount += 1
}

if (!$ErrorCount -eq 0) {
    exit 1
}
    
$imagePath = Get-Itempropertyvalue "HKLM:\SYSTEM\ControlSet001\Services\$serviceName" -Name "ImagePath"
$imagePath2 = ($imagePath -split "&s=")[1]
$machineGUID = ($imagePath2 -split "&k=")[0]
Write-Output $machineGUID