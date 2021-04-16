#CVE-2020-16898 | Windows TCP/IP Remote Code Execution Vulnerability
#https://portal.msrc.microsoft.com/en-US/security-guidance/advisory/CVE-2020-16898

#Disable IPv6 on All Adapers
Disable-NetAdapterBinding -Name "*" -ComponentID ms_tcpip6

#Confirm That all NIC's no longer have IPv6 Enabled
(Get-NetAdapterBinding -Name '*' -ComponentID ms_tcpip6).Enabled