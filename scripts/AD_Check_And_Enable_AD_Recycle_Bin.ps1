#Please only run on a domain controller
#This script will first check if there are any AD Recycle Bin scopes set up - if there are no scopes it is assumed recycle bin feature is not enabled for the domain
#The script then pulls the domain that the machine running the script is on - queries the domain for the Infrastructure Master and then will attempt to enable the feature

$adRecycleBinScope = Get-ADOptionalFeature -Identity 'Recycle Bin Feature' | Select -ExpandProperty EnabledScopes
$ADDomain = Get-ADDomain | Select -ExpandProperty Forest
$ADInfraMaster = Get-ADDomain | Select-Object InfrastructureMaster

if ($adRecycleBinScope -eq $null){
    Write-Host "Recycle Bin Disabled"
    Write-Host "Attempting to enable AD Recycle Bin"
    Enable-ADOptionalFeature -Identity 'Recycle Bin Feature' -Scope ForestOrConfigurationSet -Target $ADDomain -Server $ADInfraMaster.InfrastructureMaster -Confirm:$false
    Write-Host "AD Recycle Bin enabled for domain $($ADDomain)"
}
else{
    Write-Host "Recycle Bin already Enabled For: $($ADDomain)`n Scope: $($adRecycleBinScope)"
}