##Check if openssh is installed
if((Get-WindowsCapability -Online | ? Name -like OpenSSH*).State -eq "Installed")
	{
	Write-Host "OpenSSH Server is installed."
	}

else 

		{
	Write-Host "OpenSSH Server is NOT installed.";
	## Install SSH
	Add-WindowsCapability -Online -Name "OpenSSH.Server~~~~0.0.1.0"

	## Set SSH service to start automatically
	Set-Service -Name sshd -StartupType "Automatic"

	## Allow SSH through firewall on all profiles
	Get-NetFirewallRule -Name *ssh*

	## Start SSH service
	Start-Service sshd
	
	} 