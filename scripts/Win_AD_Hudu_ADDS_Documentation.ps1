<#
.Synopsis
   Automatically document ADDS configuration
.DESCRIPTION
   Automatically document ADDS configuration. Submits generated documentation to your Hudu instance and associates it with the Company provided by ClientName. Requires Global Keystore variables for HuduBaseDomain and HuduApiKey.
.INPUTS
    -ClientName {{client.name}}
	-HuduBaseDomain {{global.HuduBaseDomain}}
	-HuduApiKey {{global.HuduApiKey}}
.NOTES
   v1.0
   Based on https://github.com/lwhitelock/HuduAutomation/blob/main/CyberdrainRewrite/Hudu-ADDS-Documentation.ps1
.COMPONENT
   Hudu Documentation
.ROLE
   Documentation
#>

param (
  [string] $ClientName, 
  [string] $HuduBaseDomain, 
  [string] $HuduApiKey
)

if (!$ClientName) {
    write-output "Must provide -ClientName with a valid value that is identical to the name of a Company that exists in your Hudu instance. This should be the {{client.name}} value. `n"
    $ErrorCount += 1
}
if (!$HuduBaseDomain) {
    write-output "Must provide -HuduBaseUrl and it must a FQDN that maps to your Hudu instance without a trailing slash. `n"
    $ErrorCount += 1
}
if (!$HuduApiKey) {
    write-output "Must provide -HuduApiKey with a valid value from your Hudu instance. `n"
    $ErrorCount += 1
}

if (!$ErrorCount -eq 0) {
exit 1
}
#####################################################################
#
# Active Directory Details to Hudu
#
# Get a Hudu API Key from https://yourhududomain.com/admin/api_keys
# Set the base domain of your Hudu instance without a trailing /
# Client Name as it appears in Hudu
$HuduAssetLayoutName = "Active Directory - AutoDoc"
#####################################################################

Write-Host "Connecting to $HuduBaseDomain"

#Get the Hudu API Module if not installed
if (Get-Module -ListAvailable -Name HuduAPI) {
		Import-Module HuduAPI 
	} else {
		Install-Module HuduAPI -Force
		Import-Module HuduAPI
	}
  
#Set Hudu logon information
New-HuduAPIKey $HuduAPIKey
New-HuduBaseUrl $HuduBaseDomain
  
function Get-WinADForestInformation {
    $Data = @{ }
    $ForestInformation = $(Get-ADForest)
    $Data.Forest = $ForestInformation
    $Data.RootDSE = $(Get-ADRootDSE -Properties *)
    $Data.ForestName = $ForestInformation.Name
    $Data.ForestNameDN = $Data.RootDSE.defaultNamingContext
    $Data.Domains = $ForestInformation.Domains
    $Data.ForestInformation = @{
        'Name'                    = $ForestInformation.Name
        'Root Domain'             = $ForestInformation.RootDomain
        'Forest Functional Level' = $ForestInformation.ForestMode
        'Domains Count'           = ($ForestInformation.Domains).Count
        'Sites Count'             = ($ForestInformation.Sites).Count
        'Domains'                 = ($ForestInformation.Domains) -join ", "
        'Sites'                   = ($ForestInformation.Sites) -join ", "
    }
      
    $Data.UPNSuffixes = Invoke-Command -ScriptBlock {
        $UPNSuffixList  =  [PSCustomObject] @{ 
                "Primary UPN" = $ForestInformation.RootDomain
                "UPN Suffixes"   = $ForestInformation.UPNSuffixes -join ","
            }  
        return $UPNSuffixList
    }
      
    $Data.GlobalCatalogs = $ForestInformation.GlobalCatalogs
    $Data.SPNSuffixes = $ForestInformation.SPNSuffixes
      
    $Data.Sites = Invoke-Command -ScriptBlock {
      $Sites = [System.DirectoryServices.ActiveDirectory.Forest]::GetCurrentForest().Sites            
        $SiteData = foreach ($Site in $Sites) {          
          [PSCustomObject] @{ 
                "Site Name" = $site.Name
                "Subnets"   = ($site.Subnets) -join ", "
                "Servers" = ($Site.Servers) -join ", "
            }  
        }
        Return $SiteData
    }
      
        
    $Data.FSMO = Invoke-Command -ScriptBlock {
        [PSCustomObject] @{ 
            "Domain" = $ForestInformation.RootDomain
            "Role"   = 'Domain Naming Master'
            "Holder" = $ForestInformation.DomainNamingMaster
        }
 
        [PSCustomObject] @{ 
            "Domain" = $ForestInformation.RootDomain
            "Role"   = 'Schema Master'
            "Holder" = $ForestInformation.SchemaMaster
        }
          
        foreach ($Domain in $ForestInformation.Domains) {
            $DomainFSMO = Get-ADDomain $Domain | Select-Object PDCEmulator, RIDMaster, InfrastructureMaster
 
            [PSCustomObject] @{ 
                "Domain" = $Domain
                "Role"   = 'PDC Emulator'
                "Holder" = $DomainFSMO.PDCEmulator
            } 
 
             
            [PSCustomObject] @{ 
                "Domain" = $Domain
                "Role"   = 'Infrastructure Master'
                "Holder" = $DomainFSMO.InfrastructureMaster
            } 
 
            [PSCustomObject] @{ 
                "Domain" = $Domain
                "Role"   = 'RID Master'
                "Holder" = $DomainFSMO.RIDMaster
            } 
 
        }
          
        Return $FSMO
    }
      
    $Data.OptionalFeatures = Invoke-Command -ScriptBlock {
        $OptionalFeatures = $(Get-ADOptionalFeature -Filter * )
        $Optional = @{
            'Recycle Bin Enabled'                          = ''
            'Privileged Access Management Feature Enabled' = ''
        }
        ### Fix Optional Features
        foreach ($Feature in $OptionalFeatures) {
            if ($Feature.Name -eq 'Recycle Bin Feature') {
                if ("$($Feature.EnabledScopes)" -eq '') {
                    $Optional.'Recycle Bin Enabled' = $False
                }
                else {
                    $Optional.'Recycle Bin Enabled' = $True
                }
            }
            if ($Feature.Name -eq 'Privileged Access Management Feature') {
                if ("$($Feature.EnabledScopes)" -eq '') {
                    $Optional.'Privileged Access Management Feature Enabled' = $False
                }
                else {
                    $Optional.'Privileged Access Management Feature Enabled' = $True
                }
            }
        }
        return $Optional
        ### Fix optional features
    }
    return $Data
}
  
$TableHeader = "<table style=`"width: 100%; border-collapse: collapse; border: 1px solid black;`">"
$Whitespace = "<br/>"
$TableStyling = "<th>", "<th style=`"background-color:#00adef; border: 1px solid black;`">"
  
$RawAD = Get-WinADForestInformation
  
$ForestRawInfo = new-object PSCustomObject -property $RawAD.ForestInformation | convertto-html -Fragment | Select-Object -Skip 1
$ForestNice = $TableHeader + ($ForestRawInfo -replace $TableStyling) + $Whitespace
  
$SiteRawInfo = $RawAD.Sites | Select-Object 'Site Name', Servers, Subnets | ConvertTo-Html -Fragment | Select-Object -Skip 1
$SiteNice = $TableHeader + ($SiteRawInfo -replace $TableStyling) + $Whitespace
  
$OptionalRawFeatures = new-object PSCustomObject -property $RawAD.OptionalFeatures | convertto-html -Fragment | Select-Object -Skip 1
$OptionalNice = $TableHeader + ($OptionalRawFeatures -replace $TableStyling) + $Whitespace
  
$UPNRawFeatures = $RawAD.UPNSuffixes |  convertto-html -Fragment -as list| Select-Object -Skip 1
$UPNNice = $TableHeader + ($UPNRawFeatures -replace $TableStyling) + $Whitespace
  
$DCRawFeatures = $RawAD.GlobalCatalogs | ForEach-Object { Add-Member -InputObject $_ -Type NoteProperty -Name "Domain Controller" -Value $_; $_ } | convertto-html -Fragment | Select-Object -Skip 1
$DCNice = $TableHeader + ($DCRawFeatures -replace $TableStyling) + $Whitespace
  
$FSMORawFeatures = $RawAD.FSMO | convertto-html -Fragment | Select-Object -Skip 1
$FSMONice = $TableHeader + ($FSMORawFeatures -replace $TableStyling) + $Whitespace
  
$ForestFunctionalLevel = $RawAD.RootDSE.forestFunctionality
$DomainFunctionalLevel = $RawAD.RootDSE.domainFunctionality
$domaincontrollerMaxLevel = $RawAD.RootDSE.domainControllerFunctionality
  
$passwordpolicyraw = Get-ADDefaultDomainPasswordPolicy | Select-Object ComplexityEnabled, PasswordHistoryCount, LockoutDuration, LockoutThreshold, MaxPasswordAge, MinPasswordAge | convertto-html -Fragment -As List | Select-Object -skip 1
$passwordpolicyheader = "<tr><th><b>Policy</b></th><th><b>Setting</b></th></tr>"
$passwordpolicyNice = $TableHeader + ($passwordpolicyheader -replace $TableStyling) + ($passwordpolicyraw -replace $TableStyling) + $Whitespace
  
$adminsraw = Get-ADGroupMember "Domain Admins" | Select-Object SamAccountName, Name | convertto-html -Fragment | Select-Object -Skip 1
$adminsnice = $TableHeader + ($adminsraw -replace $TableStyling) + $Whitespace
  
$EnabledUsers = (Get-AdUser -filter * | Where-Object { $_.enabled -eq $true }).count
$DisabledUSers = (Get-AdUser -filter * | Where-Object { $_.enabled -eq $false }).count
$AdminUsers = (Get-ADGroupMember -Identity "Domain Admins").count
$Users = @"
There are <b> $EnabledUsers </b> users Enabled<br>
There are <b> $DisabledUSers </b> users Disabled<br>
There are <b> $AdminUsers </b> Domain Administrator users<br>
"@
 
# Setup the fields for the Asset 
$AssetFields = @{
            'domain_name'               = $RawAD.ForestName
            'forest_summary'            = $ForestNice
            'site_summary'              = $SiteNice
            'domain_controllers'        = $DCNice
            'fsmo_roles'                = $FSMONice
            'optional_features'         = $OptionalNice
            'upn_suffixes'              = $UPNNice
            'default_password_policies' = $passwordpolicyNice
            'domain_admins'             = $adminsnice
            'user_count'                = $Users
        }
 
# Checking if the FlexibleAsset exists. If not, create a new one.
$Layout = Get-HuduAssetLayouts -name $HuduAssetLayoutName

if (!$Layout) { 

$AssetLayoutFields = @(
		@{
			label = 'Domain Name'
			field_type = 'Text'
			show_in_list = 'true'
			position = 1
		},
		@{
			label = 'Forest Summary'
			field_type = 'RichText'
			show_in_list = 'false'
			position = 2
		},
		@{
			label = 'Site Summary'
			field_type = 'RichText'
			show_in_list = 'false'
			position = 3
		},
		@{
			label = 'Domain Controllers'
			field_type = 'RichText'
			show_in_list = 'false'
			position = 4
		},
		@{
			label = 'FSMO Roles'
			field_type = 'RichText'
			show_in_list = 'false'
			position = 5
		},
		@{
			label = 'Optional Features'
			field_type = 'RichText'
			show_in_list = 'false'
			position = 6
		},
		@{
			label = 'UPN Suffixes'
			field_type = 'RichText'
			show_in_list = 'false'
			position = 7
		},
		@{
			label = 'Default Password Policies'
			field_type = 'RichText'
			show_in_list = 'false'
			position = 8
		},
		@{
			label = 'Domain Admins'
			field_type = 'RichText'
			show_in_list = 'false'
			position = 9
		},
		@{
			label = 'User Count'
			field_type = 'RichText'
			show_in_list = 'false'
			position = 10
		}		
	)
	
	Write-Host "Creating New Asset Layout"
	$NewLayout = New-HuduAssetLayout -name $HuduAssetLayoutName -icon "fas fa-sitemap" -color "#00adef" -icon_color "#000000" -include_passwords $false -include_photos $false -include_comments $false -include_files $false -fields $AssetLayoutFields
	$Layout = Get-HuduAssetLayouts -name $HuduAssetLayoutName
}


$Company = Get-HuduCompanies -name $ClientName
if ($company) {	
	#Upload data to Hudu
	$Asset = Get-HuduAssets -name $RawAD.ForestName -companyid $company.id -assetlayoutid $layout.id
	
	#If the Asset does not exist, we edit the body to be in the form of a new asset, if not, we just upload.
	if (!$Asset) {
		Write-Host "New Asset Created"
		$Asset = New-HuduAsset -name $RawAD.ForestName -company_id $company.id -asset_layout_id $layout.id -fields $AssetFields	
	}
	else {
    Write-Host "Asset has been Updated"
    $Asset = Set-HuduAsset -asset_id $Asset.id -name $RawAD.ForestName -company_id $company.id -asset_layout_id $layout.id -fields $AssetFields	
	}

} else {
	Write-Host "$ClientName was not found in Hudu"
}
