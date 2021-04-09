 [CmdletBinding()]
    param ()

    begin {
        $PPNuGet = Get-PackageProvider -ListAvailable | Where-Object { $_.Name -eq 'Nuget' }
        if (!$PPNuget) {
            Write-Output 'Installing Nuget provider'
            Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.201 -Force
        }
        $PSGallery = Get-PSRepository -Name PsGallery
        if (!$PSGallery) {
            Write-Output 'Setting PSGallery as trusted Repository'
            Set-PSRepository -InstallationPolicy Trusted -Name PSGallery
        }
        $PsGetVersion = (Get-Module PowerShellGet).version
        if ($PsGetVersion -lt [version]'2.0') {
            Write-Output 'Installing latest version of PowerShellGet provider'
            Install-Module PowerShellGet -MinimumVersion 2.2 -Force
            Write-Output 'Reloading Modules'
            Remove-Module PowerShellGet -Force
            Remove-Module PackageManagement -Force
            Import-Module PowerShellGet -MinimumVersion 2.2 -Force
            Write-Output 'Updating PowerShellGet'
            Install-Module -Name PowerShellGet -MinimumVersion 2.2.3 -Force
            Write-Output 'PowerShellGet update requires all active PS Sessions to be restarted before it can continue.'
            
            Exit 1
        }
    }

    process {
        Write-Output 'Checking device Manufacturer'
        $Manufacturer = (Get-WmiObject -Class:Win32_ComputerSystem).Manufacturer
        if ($Manufacturer -like '*Dell*') {
            Write-Output 'Manufacturer is Dell. Installing Module and trying to enable Wake on LAN.'
            Write-Output 'Installing Dell Bios Provider'
            Install-Module -Name DellBIOSProvider -Force
            Import-Module DellBIOSProvider
            try {
                Set-Item -Path 'DellSmBios:\PowerManagement\WakeOnLan' -Value 'LANOnly' -ErrorAction Stop
            }
            catch {
                Write-Output 'An error occured. Was unable to set WakeOnLan.'
                
                Exit 2
            }
        }
        if ($Manufacturer -like '*HP*' -or $Manufacturer -like '*Hewlett*') {
            Write-Output 'Manufacturer is HP. Installing module and trying to enable WakeOnLan. All HP Drivers are required for this operation to succeed.'
            Write-Output 'Installing HP Provider'
            Install-Module -Name HPCMSL -Force -AcceptLicense
            Import-Module HPCMSL
            try {
                $WolTypes = get-hpbiossettingslist | Where-Object { $_.Name -like '*Wake On Lan*' }
                ForEach ($WolType in $WolTypes) {
                    Write-Output "Setting WOL Type: $($WOLType.Name)"
                    Set-HPBIOSSettingValue -name $($WolType.name) -Value 'Boot to Hard Drive' -ErrorAction Stop
                }
            }
            catch {
                Write-Output 'An error occured. Was unable to set WakeOnLan.'
                
                Exit 2
            }
        }
        if ($Manufacturer -like '*Lenovo*') {
            Write-Output 'Manufacturer is Lenovo. Trying to set via WMI. All Lenovo Drivers are required for this operation to succeed.'
            try {
                Write-Output 'Setting BIOS.'
                (Get-WmiObject -ErrorAction Stop -class 'Lenovo_SetBiosSetting' -namespace 'root\wmi').SetBiosSetting('WakeOnLAN,Primary') | Out-Null
                Write-Output 'Saving BIOS.'
                (Get-WmiObject -ErrorAction Stop -class 'Lenovo_SaveBiosSettings' -namespace 'root\wmi').SaveBiosSettings() | Out-Null
            }
            catch {
                Write-Output 'An error occured. Was unable to set WakeOnLan.'
                
                Exit 2
            }
        }
    }

    end {
        Write-Output 'Setting NIC to enable WOL'
        $NicsWithWake = Get-CimInstance -ClassName 'MSPower_DeviceWakeEnable' -Namespace 'root/wmi'
        foreach ($Nic in $NicsWithWake) {
            Write-Output 'Enabling for NIC'
            Set-CimInstance $NIC -Property @{Enable = $true }
        }
        Exit 0
    }