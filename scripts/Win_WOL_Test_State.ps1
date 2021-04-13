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
			Write-Output 'Installing PSGallery'
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
		Write-Output 'Checking Manufacturer'
		$Manufacturer = (Get-WmiObject -Class:Win32_ComputerSystem).Manufacturer
		if ($Manufacturer -like '*Dell*') {
			Write-Output 'Manufacturer is Dell. Installing Module and trying to get WOL state'
			Write-Output 'Installing Dell Bios Provider if needed'
			$Mod = Get-Module DellBIOSProvider
			if (!$mod) {
				Install-Module -Name DellBIOSProvider -Force
			}
			Import-Module DellBIOSProvider
			try {
				$WOLMonitor = Get-Item -Path 'DellSmBios:\PowerManagement\WakeOnLan' -ErrorAction SilentlyContinue
				if ($WOLMonitor.currentvalue -eq 'LanOnly') { $WOLState = 'Healthy' }
			}
			catch {
				Write-Output 'An error occured. Could not get WOL setting.'
                
                Exit 3
			}
		}
		if ($Manufacturer -like '*HP*' -or $Manufacturer -like '*Hewlett*') {
			Write-Output 'Manufacturer is HP. Installing module and trying to get WOL State.'
			Write-Output 'Installing HP Provider if needed.'
			$Mod = Get-Module HPCMSL
			if (!$mod) {
				Install-Module -Name HPCMSL -Force -AcceptLicense
			}
			Import-Module HPCMSL
			try {
				$WolTypes = get-hpbiossettingslist | Where-Object { $_.Name -like '*Wake On Lan*' }
				$WOLState = ForEach ($WolType in $WolTypes) {
					Write-Output "Setting WOL Type: $($WOLType.Name)"
					get-HPBIOSSettingValue -name $($WolType.name) -ErrorAction Stop
				}
			}
			catch {
				Write-Output 'An error occured. Could not find WOL state'
                
                Exit 3
			}
		}
		if ($Manufacturer -like '*Lenovo*') {
			Write-Output 'Manufacturer is Lenovo. Trying to get via WMI'
			try {
				Write-Output 'Getting BIOS.'
				$currentSetting = (Get-WmiObject -ErrorAction Stop -class 'Lenovo_BiosSetting' -namespace 'root\wmi') | Where-Object { $_.CurrentSetting -ne '' }
				$WOLStatus = $currentSetting.currentsetting | ConvertFrom-Csv -Delimiter ',' -Header 'Setting', 'Status' | Where-Object { $_.setting -eq 'Wake on lan' }
				$WOLStatus = $WOLStatus.status -split ';'
				if ($WOLStatus[0] -eq 'Primary') { $WOLState = 'Healthy' }
			}
			catch {
				Write-Output 'An error occured. Could not find WOL state'
                
                Exit 3
			}
		}
	}

	end {
		$NicsWithWake = Get-CimInstance -ClassName 'MSPower_DeviceWakeEnable' -Namespace 'root/wmi' | Where-Object { $_.Enable -eq $False }
		if (!$NicsWithWake) {
			$NICWOL = 'Healthy - All NICs enabled for WOL within the OS.'
            Exit 0
		}
		else {
			$NICWOL = 'Unhealthy - NIC does not have WOL enabled inside of the OS.'
            Exit 4
		}
		if (!$WOLState) {
			$NICWOL = 'Unhealthy - Could not find WOL state'
            Exit 3
		}
		return $NICWOL
	}