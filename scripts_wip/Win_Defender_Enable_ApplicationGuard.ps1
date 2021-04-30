# Script to Install Windows Defender Application Guard.
# Created by TechCentre with the help and assistance of the internet.
# Restart Required to complete install.

# Sets Variable for feature to be installed.
$FeatureName = "Windows-Defender-ApplicationGuard"  

# If Feature Installed already then skips otherwise installs.
if((Get-WindowsOptionalFeature -FeatureName $FeatureName -Online).State -eq "Enabled") {

        write-host "Installed"

    } else {

        write-host "not Installed"

Enable-WindowsOptionalFeature -online -FeatureName $FeatureName -NoRestart

    }
    