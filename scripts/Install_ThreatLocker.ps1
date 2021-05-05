param (
  [string] $organizationName,
  [string] $groupName,
  [string] $identifier
)

$groupName = $groupName.Replace("workstation","Workstations")
$groupName = $groupName.Replace("server","Servers")

if (!$identifier) {
    write-output "Global Variable not specified identifier, please create a global key store field called ThreatLockerID, Example Value: abcd3123-abc1-abc1-abc1-abcde123456 `n"
    Exit 1
}

[Net.ServicePointManager]::SecurityProtocol = "Tls12"

##
##
## DO NOT EDIT ANYTHING BELOW THIS
##
##


## Verify Identifier is added
if ($identifier -eq "XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX") {
    Write-Output "Identifier required";
    Exit 1;
}

## Check if service exists and is running
$service = Get-Service -Name ThreatLockerService -ErrorAction SilentlyContinue;

if ($service.Name -eq "ThreatLockerService" -and $service.Status -ne "Running") {
    ## If service exists and is not running, start the service
    Start-Service ThreatLockerService;
}

$service = Get-Service -Name ThreatLockerService -ErrorAction SilentlyContinue;

if ($service.Status -eq "Running") {
    ## If the service is running, exit the script
    Write-Output "Service already present";
    Exit 0;
} 
else {
    ## Check the OS type
    $osInfo = Get-CimInstance -ClassName Win32_OperatingSystem
    
    if ($osInfo.ProductType -ne 1) {
        ## If not a workstations, set the group name to Servers
        $groupName = "Servers";
    }
}

## Attempt to get the group id
try {
    $url = 'https://api.threatlocker.com/getgroupkey.ashx'; 
    $headers = @{'Authorization'=$identifier;'OrganizationName'=$organizationName;'GroupName'=$groupName}; 
    $response = (Invoke-RestMethod -Method 'Post' -uri $url -Headers $headers -Body ''); 
    $groupId = $response.split([Environment]::NewLine)[0].split(':')[1].trim();
}
catch {
    Write-Output "Failed to get GroupId";
    Exit 1;
}

## Verify the output from the group id
if ($groupId.Length -eq 24) {
    ## Check if C:\Temp directory exists and create if not
    if (!(Test-Path "C:\Temp")) {
        mkdir "C:\Temp";
    }

    ## Check the OS architecture and download the correct installer
    try {
        if ([Environment]::Is64BitOperatingSystem) {
            $downloadURL = "https://api.threatlocker.com/installers/threatlockerstubx64.exe";
        }
        else {
            $downloadURL = "https://api.threatlocker.com/installers/threatlockerstubx86.exe";
        }

        $localInstaller = "C:\Temp\ThreatLockerStub.exe";

        Invoke-WebRequest -Uri $downloadURL -OutFile $localInstaller;
    
    }
    catch {
        Write-Output "Failed to get download the installer";
        Exit 1;
    }

    ## Attempt install
    try {
        & C:\Temp\ThreatLockerStub.exe InstallKey=$groupId;
    }
    catch {
        Write-Output "Installation Failed";
        Exit 1
    }

    ## Verify install
    $service = Get-Service -Name ThreatLockerService -ErrorAction SilentlyContinue;

    if ($service.Name -eq "ThreatLockerService" -and $service.Status -eq "Running") {
        Write-Output "Installation successful";
        Exit 0;
    }
    else {
        ## Check the OS type
        $osInfo = Get-CimInstance -ClassName Win32_OperatingSystem
    
        if ($osInfo.ProductType -ne 1) {
            Write-Output "Installation Failed";
            Exit 1
        }
    }
}
else {
    Write-Output "Unable to get correct group id";
    Exit 1;
}
