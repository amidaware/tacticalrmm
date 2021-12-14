<#
.SYNOPSIS
    Installs Sophos Endpoint via the Sophos API https://developer.sophos.com/apis

.REQUIREMENTS
    You will need API credentials to use this script.  The instructions are slightly different depending who you are.
    For Partners : https://developer.sophos.com/getting-started (Only Step 1 Required For API Credentials)
    For Organizations: https://developer.sophos.com/getting-started-organization (Only Step 1 Required For API Credentials)
    For Tenants	: https://developer.sophos.com/getting-started-tenant (Only Step 1 Required For API Credentials)

.INSTRUCTIONS
    1. Get your API Credentials (Client Id, Client Secret) using the steps in the Requirements section
    2. In Tactical RMM, Go to Settings >> Global Settings >> Custom Fields and under Clients, create the following custom fields: 
        a) SophosTenantName as type text
        b) SophosClientId as type text
        c) SophosClientSecret as type text
    3. In Tactical RMM, Right-click on each client and select Edit.  Fill in the SophosTenantName, SophosClientId, and SophosClientSecret.  
       Make sure the SophosTenantName is EXACTLY how it is displayed in your Sophos Partner / Central Dashboard.  A partner can find the list of tenants on the left menu under Sophos Central Customers
    4. Create the follow script arguments
        a) -ClientId {{client.SophosClientId}}
        b) -ClientSecret {{client.SophosClientSecret}}
        c) -TenantName {{client.SophosTenantName}}
        d) -Products (Optional Parameter) - A list of products to install, comma-separated.  Available options are: antivirus, intercept, mdr, deviceEncryption or all.  Example - To install Antivirus, Intercept, and Device encryption you would pass "antivirus,intercept,deviceEncryption".  
		
.NOTES
	V1.0 Initial Release by https://github.com/bc24fl/tacticalrmm-scripts/
	V1.1 Added error handling for each Invoke-Rest Call for easier troubleshooting and graceful exit.
	V1.2 Added support for more than 100 tenants.
	
#>

param(
    $ClientId,
    $ClientSecret,
    $TenantName,
    $Products
)

if ([string]::IsNullOrEmpty($ClientId)) {
    Write-Output "ClientId must be defined. Use -ClientId <value> to pass it."
    Exit 1
}

if ([string]::IsNullOrEmpty($ClientSecret)) {
    Write-Output "ClientSecret must be defined. Use -ClientSecret <value> to pass it."
    Exit 1
}

if ([string]::IsNullOrEmpty($TenantName)) {
    Write-Output "TenantName must be defined. Use -TenantName <value> to pass it."
    Exit 1
}

if ([string]::IsNullOrEmpty($Products)) {
    Write-Output "No product options specified installing default antivirus and intercept."
    $Products = "antivirus,intercept"
}

Write-Host "Running Sophos Endpoint Installation Script On: $env:COMPUTERNAME"

# Find if workstation or server.  osInfo.ProductType returns 1 = workstation, 2 = domain controller, 3 = server
$osInfo = Get-CimInstance -ClassName Win32_OperatingSystem

$urlAuth = "https://id.sophos.com/api/v2/oauth2/token"
$urlWhoami = "https://api.central.sophos.com/whoami/v1"
$urlTenant = "https://api.central.sophos.com/partner/v1/tenants?pageTotal=true"

$authBody = @{
    "grant_type"="client_credentials"
    "client_id"=$ClientId
    "client_secret"=$ClientSecret
    "scope"="token"
}

$authResponse = (Invoke-RestMethod -Method 'post' -Uri $urlAuth -Body $authBody)
$authToken = $authResponse.access_token
$authHeaders = @{Authorization = "Bearer $authToken"}

if ($authToken.length -eq 0){
	Write-Host "Error, no authentication token received.  Please check your api credentials.  Exiting script."
	Exit 1
}

$whoAmIResponse = (Invoke-RestMethod -Method 'Get' -headers $authHeaders -Uri $urlWhoami)
$myId = $whoAmIResponse.Id
$myIdType = $whoAmIResponse.idType

if ($myIdType.length -eq 0){
	Write-Host "Error, no Whoami Id Type received.  Please check your api credentials or network connections.  Exiting script."
	Exit 1
}

if($myIdType -eq 'partner'){
    $requestHeaders =@{
        'Authorization'="Bearer $authToken"
        'X-Partner-ID'=$myId
    }
}
elseif($myIdType -eq 'organization') {
    $requestHeaders =@{
        'Authorization' = "Bearer $authToken"
        'X-Organization-ID' = $myId
    }
}
elseif($myIdType -eq 'tenant'){
    $requestHeaders =@{
        'Authorization' = "Bearer $authToken"
        'X-Tenant-ID' = $myId
    }
}
else {
    Write-Host "Error finding id type.  This script only supports Partner, Organization, and Tenant API's."
    Exit 1
}

# Cycle through all tenants until a tenant match, or all pages have exhausted.  
$currentPage = 1
do {
	Write-Output "Looking for tenant on page $currentPage.  Please wait..."
	
	if ($currentPage -ge 2){
		Start-Sleep -s 5
		$urlTenant 	= "https://api.central.sophos.com/partner/v1/tenants?page=$currentPage"
	}
	
	$tenantResponse = (Invoke-RestMethod -Method 'Get' -headers $requestHeaders -Uri $urlTenant)
	$tenants = $tenantResponse.items
	$totalPages	= [int]$tenantResponse.pages.total
	
	foreach ($tenant in $tenants) {
		if ($tenant.name -eq $TenantName){
			$tenantRegion = $tenant.dataRegion
			$tenantId = $tenant.id
		}
	}
	$currentPage += 1
} until( $currentPage -gt $totalPages -Or ($tenantId.length -gt 1 ) )

if ($tenantId.length -eq 0){
	Write-Host "Error, no tenant found with the provided name.  Please check the name and try again.  Exiting script."
	Exit 1
}

$requestHeaders =@{
    'Authorization' = "Bearer $authToken"
    'X-Tenant-ID' = $tenantId 
}

$urlEndpoint = "https://api-" + $tenantRegion + ".central.sophos.com/endpoint/v1/downloads"
$endpointDownloadResponse = (Invoke-RestMethod -Method 'Get' -headers $requestHeaders -Uri $urlEndpoint)
$endpointInstallers = $endpointDownloadResponse.installers

if ($endpointInstallers.length -eq 0){
	Write-Host "Error, no installers received.  Please check your api credentials or network connections.  Exiting script."
	Exit 1
}

foreach ($installer in $endpointInstallers){
    
    if ( ($installer.platform -eq "windows") -And ($installer.productName = "Sophos Endpoint Protection") ){
        
        if ( ($osInfo.ProductType -eq 1) -And ($installer.type = "computer") ){
		# Workstation Install
            $installUrl = $installer.downloadUrl
        }
        elseif ( ( ($osInfo.ProductType -eq 2) -Or ($osInfo.ProductType -eq 3) ) -And ($installer.type = "server") ){
		# Server Install
            $installUrl = $installer.downloadUrl
        }
        else{
            Write-Host "Error, this script only supports producttype of 1) Work Station, 2) Domain Controller, or 3) Server."
            Exit 1
        }
    }
}

try{
    Write-Host "Checking if Sophos Endpoint installed.  Please wait..."
    $AppInstalled = & "choco" "list" "-li"

    if ($AppInstalled -like '*Sophos Endpoint Agent*'){
        Write-Host "Sophos Endpoint is installed.  Skipping installation."
    } else {
        Write-Host "Sophos Endpoint is NOT installed.  Installing now..."

        Write-Host "Downloading Sophos from " + $installUrl + " Please wait..." 
        $tmpDir = [System.IO.Path]::GetTempPath()
    
        $outpath = $tmpDir + "SophosSetup.exe"
        
        Write-Host "Saving file to " + $outpath
        
        Invoke-WebRequest -Uri $installUrl -OutFile $outpath

        Write-Host "Running Sophos Setup... Please wait up to 20 minutes for install to complete." 
        $appArgs = @("--products=" + $Products + " --quiet ")
        Start-Process -Filepath $outpath -ArgumentList $appArgs
    }
}
catch{
    Write-Host "Installation failed with error message: $($PSItem.ToString())"
}
