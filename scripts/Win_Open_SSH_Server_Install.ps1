if((Get-WindowsCapability -Online | ? Name -like OpenSSH.Server*).State -eq "Installed") {
	Write-Output "OpenSSH Server is already installed."
} else {
    Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
    Set-Service -Name sshd -StartupType 'Automatic'
    Start-Service sshd
}
Get-WindowsCapability -Online | Where-Object -Property Name -Like "OpenSSH*"
