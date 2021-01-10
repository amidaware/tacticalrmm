# Verifies that script is running on Windows 10 or greater
function Check-IsWindows10
{
    if ([System.Environment]::OSVersion.Version.Major -ge "10") 
    {
        Write-Output $true
    }
    else
    {
        Write-Output $false
    }
}

# Verifies that script is running on Windows 10 1709 or greater
function Check-IsWindows10-1709
{
    if ([System.Environment]::OSVersion.Version.Minor -ge "16299") 
    {
        Write-Output $true
    }
    else
    {
        Write-Output $false
    }
}

function SetRegistryKey([string]$key, [int]$value)
{
    #Editing Windows Defender settings AV via registry is NOT supported. This is a scripting workaround instead of using Group Policy or SCCM for Windows 10 version 1703
    $amRegistryPath = "HKLM:\Software\Policies\Microsoft\Microsoft Antimalware\MpEngine"
    $wdRegistryPath = "HKLM:\Software\Policies\Microsoft\Windows Defender\MpEngine"
    $regPathToUse = $wdRegistryPath #Default to WD path
    if (Test-Path $amRegistryPath)
    {
        $regPathToUse = $amRegistryPath
    }
    New-ItemProperty -Path $regPathToUse -Name $key -Value $value -PropertyType DWORD -Force | Out-Null
} 

#### Setup Windows Defender Secure Settings

# Start Windows Defender Service
Set-Service -Name "WinDefend" -Status running -StartupType automatic
Set-Service -Name "WdNisSvc" -Status running -StartupType automatic

#  Enable real-time monitoring
Set-MpPreference -DisableRealtimeMonitoring 0

# Enable cloud-deliveredprotection# 
Set-MpPreference -MAPSReporting Advanced

# Enable sample submission# 
Set-MpPreference -SubmitSamplesConsent 1

# Enable checking signatures before scanning# 
Set-MpPreference -CheckForSignaturesBeforeRunningScan 1

# Enable behavior monitoring# 
Set-MpPreference -DisableBehaviorMonitoring 0

# Enable IOAV protection# 
Set-MpPreference -DisableIOAVProtection 0

# Enable script scanning# 
Set-MpPreference -DisableScriptScanning 0

# Enable removable drive scanning# 
Set-MpPreference -DisableRemovableDriveScanning 0

# Enable Block at first sight# 
Set-MpPreference -DisableBlockAtFirstSeen 0

# Enable potentially unwanted apps# 
Set-MpPreference -PUAProtection Enabled

# Schedule signature updates every 8 hours# 
Set-MpPreference -SignatureUpdateInterval 8

# Enable archive scanning# 
Set-MpPreference -DisableArchiveScanning 0

# Enable email scanning# 
Set-MpPreference -DisableEmailScanning 0

if (!(Check-IsWindows10-1709))
{
    # Set cloud block level to 'High'# 
    Set-MpPreference -CloudBlockLevel High

    # Set cloud block timeout to 1 minute# 
    Set-MpPreference -CloudExtendedTimeout 50

    Write-Host # `nUpdating Windows Defender Exploit Guard settings`n#  -ForegroundColor Green 

    Write-Host # Enabling Controlled Folder Access and setting to block mode# 
    Set-MpPreference -EnableControlledFolderAccess Enabled 

    Write-Host # Enabling Network Protection and setting to block mode# 
    Set-MpPreference -EnableNetworkProtection Enabled

    Write-Host # Enabling Exploit Guard ASR rules and setting to block mode# 
    Add-MpPreference -AttackSurfaceReductionRules_Ids 75668C1F-73B5-4CF0-BB93-3ECF5CB7CC84 -AttackSurfaceReductionRules_Actions Enabled
    Add-MpPreference -AttackSurfaceReductionRules_Ids 3B576869-A4EC-4529-8536-B80A7769E899 -AttackSurfaceReductionRules_Actions Enabled
    Add-MpPreference -AttackSurfaceReductionRules_Ids D4F940AB-401B-4EfC-AADC-AD5F3C50688A -AttackSurfaceReductionRules_Actions Enabled
    Add-MpPreference -AttackSurfaceReductionRules_Ids D3E037E1-3EB8-44C8-A917-57927947596D -AttackSurfaceReductionRules_Actions Enabled
    Add-MpPreference -AttackSurfaceReductionRules_Ids 5BEB7EFE-FD9A-4556-801D-275E5FFC04CC -AttackSurfaceReductionRules_Actions Enabled
    Add-MpPreference -AttackSurfaceReductionRules_Ids BE9BA2D9-53EA-4CDC-84E5-9B1EEEE46550 -AttackSurfaceReductionRules_Actions Enabled
    Add-MpPreference -AttackSurfaceReductionRules_Ids 92E97FA1-2EDF-4476-BDD6-9DD0B4DDDC7B -AttackSurfaceReductionRules_Actions Enabled

    if ($false -eq (Test-Path ProcessMitigation.xml))
    {
        Write-Host # Downloading Process Mitigation file from https://demo.wd.microsoft.com/Content/ProcessMitigation.xml# 
        $url = 'https://demo.wd.microsoft.com/Content/ProcessMitigation.xml'
        Invoke-WebRequest $url -OutFile ProcessMitigation.xml
    }

    Write-Host # Enabling Exploit Protection# 
    Set-ProcessMitigation -PolicyFilePath ProcessMitigation.xml

}

else
{
    # #  Workaround for Windows 10 version 1703
    # Set cloud block level to 'High'# 
    SetRegistryKey -key MpCloudBlockLevel -value 2

    # Set cloud block timeout to 1 minute# 
    SetRegistryKey -key MpBafsExtendedTimeout -value 50
}

Write-Host # `nSettings update complete#   -ForegroundColor Green

Write-Host # `nOutput Windows Defender AV settings status#   -ForegroundColor Green
Get-MpPreference
