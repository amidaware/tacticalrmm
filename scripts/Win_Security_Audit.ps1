# boilerplate
[int]$varBuildString=50
[int]$varKernel = ([System.Diagnostics.FileVersionInfo]::GetVersionInfo("C:\Windows\system32\kernel32.dll")).FileBuildPart
$ErrorActionPreference = "stop"
$varTimeZone=(get-itemproperty 'HKLM:\SYSTEM\CurrentControlSet\Control\TimeZoneInformation' -Name TimeZoneKeyName).TimeZoneKeyName -replace '[^a-zA-Z:()\s]',"-"
$varPSVersion= "PowerShell version: " + $PSVersionTable.PSVersion.Major + '.' + $PSVersionTable.PSVersion.Minor
[int]$varDomainRole=(Get-WmiObject -Class Win32_ComputerSystem).DomainRole
[int]$varWarnings=0
[int]$varAlerts=0

if (!([System.Diagnostics.EventLog]::SourceExists("Security Audit"))) {
    New-EventLog -LogName 'Application' -Source 'Security Audit'
}

# preliminary pabulum
write-host "Security Audit: build $varBuildString"
write-host `r
write-host "Local Time:        " (get-date)
write-host "Local Timezone:    " $varTimeZone
write-host "Windows Version:    Build $varKernel`:" (get-WMiObject -computername $env:computername -Class win32_operatingSystem).caption
write-host $varPSVersion

# workgroup/domain
if (!(Get-WmiObject -Class Win32_ComputerSystem).PartOfDomain) {
    if ((Get-WmiObject -Class Win32_ComputerSystem).Workgroup -match 'WORKGROUP') {
        write-host "Workgroup:          Default Workgroup Setting `(`"WORKGROUP`"`)"
    } else {
        write-host "Workgroup:         "(Get-WmiObject -Class Win32_ComputerSystem).Workgroup
    }
} else {
    write-host "Domain:            "(Get-WmiObject -Class Win32_ComputerSystem).Domain
}

write-host "============================================================================="
write-host `r

# kernel
if ($varKernel -lt 7601) {
    write-host "- ALERT: This Component only runs on devices running Windows 7 SP1/Server 2008 R2 and higher."
    write-host "  Please update this device."
    $varAlerts++
    Write-EventLog -LogName 'Application' -Source 'Security Audit' -EntryType Error -EventID 59101 -Message "Security Audit Alert: This OS is not supported by Microsoft and will not be receiving Security Updates.`rIt is crucial that this device is upgraded or decommissioned as soon as possible.`rThe audit cannot proceed."
    exit
}

if ($varKernel -eq 7601) {
    if ($varDomainRole -gt 1) {
        # windows 7 timeout
        write-host "- ALERT: Support for Windows 7 was discontinued on the 14th of January 2020."
        write-host "  This device will not receive security updates and should be upgraded or decommissioned."
        write-host "  Microsoft will provide extended support for this Operating System at a cost until 2023."
    } else {
        write-host "- ALERT: Support for Windows Server 2008 R2 was discontinued on the 14th of January 2020."
        write-host "  This can be mitigated for three years by moving to Azure; if this device has already been"
        write-host "  migrated to Azure, this message can be disregarded until 2023."
    }
    $varAlerts++
    write-host `r
    Write-EventLog -LogName 'Application' -Source 'Security Audit' -EntryType Error -EventID 59103 -Message "Security Audit Alert: This OS is not supported by Microsoft and will not be receiving Security Updates.`rIt is crucial that this device is upgraded or decommissioned as soon as possible."
}

if ($varKernel -eq 9200) {
    if ($varDomainRole -gt 1) {
        write-host "- ALERT: Windows 8.0 has been discontinued by Microsoft." #server 2012 still supported until 2023
        write-host "  Please update this device to Windows 8.1 or Windows 10."
        $varAlerts++
        write-host `r
        Write-EventLog -LogName 'Application' -Source 'Security Audit' -EntryType Error -EventID 59103 -Message "Security Audit Alert: This OS is not supported by Microsoft and will not be receiving Security Updates.`rIt is crucial that this device is upgraded or decommissioned as soon as possible."
    }
}

write-host "= Account Security Audit ----------------------------------------------------"

# is admin account disabled?
$localAccountExists = Get-WmiObject -Class Win32_UserAccount -Filter "LocalAccount='$true'"
If ( -not $localAccountExists ) {
    write-host "+ No Local Accounts (Admin, Guest) exist on this device."
} else {
    #is guest acct disabled?
    if ((Get-WmiObject -Class Win32_UserAccount -Filter "LocalAccount='$true' AND SID LIKE '%-501'").disabled) {
        write-host "+ The Guest account is disabled."
    } else {
        write-host "- ALERT: The Guest account is enabled."
        write-host "  Guest accounts are considered unsafe and should be disabled on this device."
        $varAlerts++
        Write-EventLog -LogName 'Application' -Source 'Security Audit' -EntryType Warning -EventID 59104 -Message "Security Audit Warning: The Guest account is enabled on this device.`rThis unprotected user account can be used as a vantage point by malware and should be disabled."
    }

    #is admin acct disabled?
    if ((Get-WmiObject -Class Win32_UserAccount -Filter "LocalAccount='$true' AND SID LIKE '%-500'").disabled) {
        write-host "+ The Administrator account is disabled."
    } else {
        write-host "- ALERT: The Administrator account is enabled."
        write-host "  Management should be handled by a domain administrator and not the local user."
        $varAlerts++
        Write-EventLog -LogName 'Application' -Source 'Security Audit' -EntryType Warning -EventID 59105 -Message "Security Audit Warning: The local Administrator account is enabled on this device.`rThis can be used as a vantage point by malware and should be disabled."
    }


    # are all accounts in the administrators group disabled? v2: ps2 compat
    $arrLocalAdmins=@()
    (Get-WMIObject -Class Win32_Group -Filter "LocalAccount=TRUE and SID='S-1-5-32-544'").GetRelated("Win32_Account","","","","PartComponent","GroupComponent",$FALSE,$NULL) | where-object {$_.Domain -match $env:COMPUTERNAME} | ForEach-Object {
        $varCurrentName=$_.Name
        if (!(Get-WmiObject -Class Win32_UserAccount -filter "Name like '$varCurrentName' AND LocalAccount=TRUE" | % {$_.disabled})) {
            $arrLocalAdmins += ($varCurrentName -as [string])
        }
    }

    $arrLocalAdmins = $arrLocalAdmins | where {$_ -match "\w"}
    if ($arrLocalAdmins) {
        $varWarnings++
        write-host "- WARNING: The following local users are within the `'Administrators`' user group:"
        foreach ($iteration in $arrLocalAdmins) {
            write-host ":  $iteration"
            if ((Get-WmiObject -Class Win32_ComputerSystem).PartOfDomain) {
                Write-EventLog -LogName 'Application' -Source 'Security Audit' -EntryType Warning -EventID 59106 -Message "Security Audit Warning: The local user `"$iteration`" is listed as an Administrator.`rLocal users should not have device-level administrative privileges; devices should be governed by the network administrator."
            } else {
                Write-EventLog -LogName 'Application' -Source 'Security Audit' -EntryType Warning -EventID 59106 -Message "Security Audit Warning: The local user `"$iteration`" is listed as an Administrator.`rLocal users should not have device-level administrative privileges; the device should be part of, and governed by, a domain."
            }
        }
    } else {
        write-host "+ No accounts within the `'Administrators`' group have local access."
    }
}

if ((Get-WmiObject -Class Win32_ComputerSystem).PartOfDomain) {
	write-host "- WARNING: This device is part of an AD domain."
	write-host "  If it has not been done already, consider enabling the user-level Active Directory setting"
	write-host "  `'Account is sensitive and cannot be delegated`' to mitigate the spread of malware via token impersonation."
	write-host '  More info: https://www.theregister.co.uk/2018/12/03/notpetya_ncc_eternalglue_production_network/'
    $varWarnings++
}

# net accounts, since we're not doing anything with the data besides displaying it

write-host `r
write-host "= Password Policy Audit -----------------------------------------------------"
if (!(Get-WmiObject -Class Win32_ComputerSystem).PartOfDomain) {
    foreach ($iteration in (net accounts | where {$_ -match "\w"})) {
        if ($iteration -match ":") {write-host : $iteration}
    }
} else {
    write-host ": Skipping local password policy audit as device will use domain-enforced policy settings."
}

# default password for automatic logon
try {
    $varDefaultPassLength=((get-itemproperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon' -Name defaultPassword).defaultPassword).length
    $varDefaultPass=(get-itemproperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon' -Name defaultPassword).defaultPassword
    $varDefaultUser="undefined"
    $varDefaultUser=(get-itemproperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon' -Name defaultUserName).defaultUserName
    write-host "`- ALERT: A user password is being stored in the Registry in plaintext `($varDefaultPassLength characters.`)"
    write-host "  It is stored in HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon under value `"DefaultPassword`"."
    $varAlerts++
    Write-EventLog -LogName 'Application' -Source 'Security Audit' -EntryType Warning -EventID 59107 -Message "Security Audit Warning: Account password for user `"$varDefaultUser`" stored in plaintext in Registry.`rThe user appears to have configured their device to log into their user account automatically via the Registry.`rTheir password is stored in plaintext at HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon under value `"DefaultPassword`" and should be removed ASAP."
    #since we have the password, may as well analyse it
    # -- length
    if ($varDefaultPassLength -le 7) {
        write-host "> As the password for username `"$varDefaultUser`" is readily available, it has been analysed for length."
        write-host "  The user's password is fewer than 8 characters."
        write-host "  A longer password - or stronger password policies - should be regimented."
        Write-EventLog -LogName 'Application' -Source 'Security Audit' -EntryType Warning -EventID 59108 -Message "Security Audit Warning: Since the password for user `"$varDefaultUser`" is stored in plaintext in the Registry, it's been analysed for length.`rThe password is fewer than 8 characters in length. Implement a stronger password or stronger password policy settings."
    }
    # -- strength
    if ($varDefaultPass -match 'password' -or $varDefaultPass -match 'p4ssw0rd' -or $varDefaultPass -match '12345' -or $varDefaultPass -match 'qwerty' -or $varDefaultPass -match 'letmein') {
        write-host "> As the password for username `"$varDefaultUser`" is readily available, it has been analysed for strength."
        write-host "  The user's password is one of many known common passwords."
        write-host "  A more unique password - or stronger password policies - should be regimented."
        Write-EventLog -LogName 'Application' -Source 'Security Audit' -EntryType Error -EventID 59109 -Message "Security Audit Alert: Since the password for user `"$varDefaultUser`" is stored in plaintext in the Registry, it's been analysed for security.`rThe password is one of many very well-known common password strings. Implement a more unique password or stronger password policy settings."
    }
} catch [System.Exception] {
    write-host "+ No account credentials are stored in the Registry."
}

write-host `r
write-host "= Network Security Audit ----------------------------------------------------"

# Restrict Null Session Access Value in Registry (shares that are accessible anonymously)
try {
    $varNullSession=(Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Services\LanManServer\Parameters').restrictnullsessaccess
    if ($varNullSession -ne 1) {
        write-host "- ALERT: Device does not restrict access to anonymous shares. This poses a security risk."
        $varAlerts++
        Write-EventLog -LogName 'Application' -Source 'Security Audit' -EntryType Warning -EventID 59110 -Message "Security Audit Warning: Access to anonymous shares is permitted and should be disabled.`rThe setting is stored in the Registry at HKLM:\SYSTEM\CurrentControlSet\Services\LanManServer\Parameters under value `"RestrictNullSessAccess`"."
    } else {
        write-host "+ Device restricts access to anonymous shares."
    }
} catch [System.Exception] {
    write-host ": Unable to determine whether this device restricts access to anonymous shares."
}

# is telnet server enabled
get-process tlntsvr -erroraction silentlycontinue | out-null
if ($?) {
	write-host "- ALERT: Telnet Server is active."
	write-host "  Telnet is considered insecure as commands are sent in plaintext. Consider using a more secure alternative."
    $varAlerts++
    Write-EventLog -LogName 'Application' -Source 'Security Audit' -EntryType Warning -EventID 59111 -Message "Security Audit Warning: Telnet Server is running and should be replaced by a more secure alternative."
} else {
	write-host "+ Telnet Server is not installed."
}

# is SMBv1 permitted?
# - server
try {
    $varSMBCheck=(Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters').SMB1
    if ($varSMBCheck -eq 1) {
        write-host "- ALERT: Device is configured as an SMBv1 server."
        write-host "  This is a huge security risk. This protocol is actively exploited by malware."
        $varAlerts++
        Write-EventLog -LogName 'Application' -Source 'Security Audit' -EntryType Warning -EventID 59112 -Message "Security Audit Warning: Device serves using the vulnerable and actively-exploited SMBv1 protocol.`rMicrosoft advisory: https://blogs.technet.microsoft.com/filecab/2016/09/16/stop-using-smb1/"
    } else {
        write-host "+ Device is not configured as an SMBv1 server."
    }
} catch [System.Exception] {
    write-host "+ Device is not configured as an SMBv1 server."
}

# - client (https://support.microsoft.com/en-us/help/2696547/how-to-detect-enable-and-disable-smbv1-smbv2-and-smbv3-in-windows-and)
$varClientSMB1=(get-service lanmanserver).requiredservices | where-object {$_.DisplayName -match '1.xxx'}
if ($varClientSMB1) {
    write-host "- ALERT: Device is configured as an SMBv1 client."
    write-host "  This is a huge security risk. This protocol is actively exploited by malware."
    $varAlerts++
    Write-EventLog -LogName 'Application' -Source 'Security Audit' -EntryType Warning -EventID 59113 -Message "Security Audit Warning: Device is configured as a client for the vulnerable and actively-exploited SMBv1 protocol.`rMicrosoft advisory: https://blogs.technet.microsoft.com/filecab/2016/09/16/stop-using-smb1/"
} else {
        write-host "+ Device is not configured as an SMBv1 client."
}

# windows firewall

# do you really think there's anybody out there?
if (((Get-WmiObject win32_service  -Filter "name like '%mpssvc%'").state) -match 'Running') {
    write-host "+ Windows Firewall is running:"
    $varFirewallRunning=$true
} else {
    write-host "- ALERT: Windows Firewall is not running."
    write-host "  Unless a third-party Firewall program is running in its stead, please re-enable it."
    $varAlerts++
    Write-EventLog -LogName 'Application' -Source 'Security Audit' -EntryType Warning -EventID 59119 -Message "Security Audit Warning: Windows Firewall is not running.`rIf this was unintentional, please re-enable Windows Firewall.`rIf this was intentional, please ensure the replacement solution is operational and configured."
}

# - firewall enabled for private networks?
try {
    $varSMBCheck=(Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Services\SharedAccess\Parameters\FirewallPolicy\StandardProfile').EnableFirewall
    if ($varSMBCheck -ne 1) {
        write-host "-  ALERT: Windows Firewall is disabled for Private networks."
        $varAlerts++
        Write-EventLog -LogName 'Application' -Source 'Security Audit' -EntryType Warning -EventID 59116 -Message "Security Audit Warning: Windows Firewall is disabled for Private networks.`rIf this was unintentional, please revert the setting.`rIf this was intentional, please ensure the replacement solution is operational and configured."
    } else {
        write-host "+  Windows Firewall is enabled for Private networks."
    }
} catch [System.Exception] {
    write-host "-  ALERT: Unable to ascertain Windows Firewall state for Private networks."
    $varAlerts++
}

# - firewall enabled for public networks?
try {
    $varSMBCheck=(Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Services\SharedAccess\Parameters\FirewallPolicy\PublicProfile').EnableFirewall
    if ($varSMBCheck -ne 1) {
        write-host "-  ALERT: Windows Firewall is disabled for Public networks."
        $varAlerts++
        Write-EventLog -LogName 'Application' -Source 'Security Audit' -EntryType Warning -EventID 59117 -Message "Security Audit Warning: Windows Firewall is disabled for Public networks.`rIf this was unintentional, please revert the setting.`rIf this was intentional, please ensure the replacement solution is operational and configured."
    } else {
        write-host "+  Windows Firewall is enabled for Public networks."
    }
} catch [System.Exception] {
    write-host "-  ALERT: Unable to ascertain Windows Firewall state for Public networks."
    $varAlerts++
}

# - firewall is enabled when connected to a domain?
if ((Get-WmiObject -Class Win32_ComputerSystem).PartOfDomain) {
    try {
        $varSMBCheck=(Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Services\SharedAccess\Parameters\FirewallPolicy\DomainProfile').EnableFirewall
        if ($varSMBCheck -ne 1) {
            write-host "-  ALERT: Windows Firewall is disabled for Domains."
            $varAlerts++
            Write-EventLog -LogName 'Application' -Source 'Security Audit' -EntryType Warning -EventID 59118 -Message "Security Audit Warning: Windows Firewall is disabled for Domains.`rIf this was unintentional, please revert the setting.`rIf this was intentional, please ensure the replacement solution is operational and configured."
        } else {
            write-host "+  Windows Firewall is enabled for Domains."
        }
    } catch [System.Exception] {
        write-host "-  ALERT: Unable to ascertain Windows Firewall state for Domains."
        $varAlerts++
    }
} else {
    write-host ":  Device is not part of a domain; checks for domain-level firewall compliance skipped."
}

# - show active profiles. this will read strangely but it's the only way to do it without butchering the i18n
if ($varFirewallRunning) {
    write-host "= Active Windows Firewall Profile Settings (from NETSH):"
    foreach ($iteration in (netsh advfirewall show currentprofile | select-string ":" | select-string " ")) {
        $varActiveProfile = $iteration -as [string]
        write-host ": " $varActiveProfile.substring(0,$varActiveProfile.Length-2)
    }
} else {
    write-host ": Not showing active Windows Firewall profile/s as Windows Firewall is not running."
}

# teamviewer
Get-ChildItem "C:\Users" | ?{ $_.PSIsContainer } | % { 
    if (test-path "C:\Users\$_\AppData\Roaming\TeamViewer\Connections.txt") {
        write-host "- WARNING: User `"$_`" has used TeamViewer software."
        write-host "  While TeamViewer is not inherently unsafe, any remote connection should be scrutinised."
        $varTeamViewer=$true
        $varWarnings++
    }
}
if (!$varTeamViewer) {
    write-host "+ TeamViewer has not been used on this device. (All connections should go via Datto RMM.)"
}

write-host `r
write-host "= Device Security Audit -----------------------------------------------------"

if ($varKernel -ge 9200) {
    try {
        $varSecureBoot=Confirm-SecureBootUEFI
        if ($varSecureBoot) {
            write-host "+  UEFI Secure Boot is supported and enabled on this device."
        } else {
            write-host "-  ALERT: UEFI Secure Boot is supported but not enabled on this device."
            write-host "   This setting should be enabled to prevent malware from interfering with the Windows boot process."
            $varAlerts++
            Write-EventLog -LogName 'Application' -Source 'Security Audit' -EntryType Warning -EventID 59114 -Message "Security Audit Warning: UEFI Secure Boot is supported on this device but has not been enabled.`rThis may have been configured deliberately to facilitate installation of other Operating Systems that do not have a Microsoft Secure Boot shim available; however, the setting still leaves a device vulnerable and should be changed."
        }
    } catch [PlatformNotSupportedException] {
        write-host ":  UEFI Secure Boot is not supported on this device."
        write-host "   The device may use the legacy BIOS platform instead of UEFI or it may be a virtual machine."
    }
} else {
    write-host ":  UEFI Secure Boot is not supported on Windows 7."
}

write-host "= Windows 10 Exploit Protection settings:"

if ($varKernel -ge 16299) {
    $varExploitProtection=Get-ProcessMitigation -System
    if ($varExploitProtection.DEP.Enable -match 'OFF') {$varExploitFlaws+="Enable DEP / "}
    if ($varExploitProtection.CFG.Enable -match 'OFF') {$varExploitFlaws+="Enable Control Flow Guard / "}
    if ($varExploitProtection.ASLR.BottomUp -match 'OFF') {$varExploitFlaws+="Enable Bottom-up ASLR / "}
    if ($varExploitProtection.ASLR.HighEntropy -match 'OFF') {$varExploitFlaws+="Enable High-Entropy ASLR / "}
    if ($varExploitProtection.SEHOP.Enable -match 'OFF') {$varExploitFlaws+="Enable Exception Chain Validation (SEHOP) / "}
    if ($varExploitProtection.Heap.TerminateOnError -match 'OFF') {$varExploitFlaws+="Enable Heap Integrity Validation"}

    if ($varExploitFlaws) {
        write-host "-  WARNING: System Exploit Protection configuration differs from Windows 10 Exploit Protection Settings."
        write-host "   These settings were configured deliberately, most likely in response to a compatibility conflict."
        write-host "   Mitigation steps are listed below. Compare them closely with your system configuration."
        write-host ":  $varExploitFlaws"
        $varWarnings++
        Write-EventLog -LogName 'Application' -Source 'Security Audit' -EntryType Warning -EventID 59115 -Message "Security Audit Warning: Windows 10 Exploit Protection settings have been altered from the default.`rThis is generally done deliberately by the end-user or administrator in order to mitigate against a specific compatibility or performance issue.`rRegardless, it is bad practice to deviate from Microsoft's standards. Please scrutinise the mitigation steps below and ensure you have a strong justification for dismissing each.`r$varExploitFlaws"
    } else {
        write-host "+  Main Windows 10 Exploit Protection Settings have not been altered from default recommendations."
    }
} else {
    write-host ":  Windows 10 Exploit Protection is only available from Windows 10 build 1709 onward."
    write-host "   Older systems may benefit from the Microsoft Enhanced Mitigation Toolkit (EMET)."
}

#security policy I: get the data
[array]$arrSecurityPolicies=@()
try {
    Get-ChildItem -Recurse 'HKLM:\SOFTWARE\Policies\Microsoft\Windows\Safer\codeidentifiers\0\Paths' | % {
       [array]$arrSecurityPolicies += (Get-ItemProperty registry::$_).ItemData
    }
} catch [System.Exception] {
    write-host "- ALERT: Device contains no security policies. These can be used to halt execution of hazardous file types."
    write-host "  Please consider blocking execution of CPL, SCR, VBS and the Right-to-Left Override character in SecPol.msc."
    $varAlerts++
    Write-EventLog -LogName 'Application' -Source 'Security Audit' -EntryType Error -EventID 59120 -Message "Security Audit Alert: The Windows Security Policy is not configured to block files with dangerous extensions from executing.`rThese file types are: $varFileRisks`.`rIn addition, the right-to-left unicode character should also be blocked to mitigate against extension masquerade attacks.`rMore information: https://www.ipa.go.jp/security/english/virus/press/201110/E_PR201110.html"
    $varNoSecPols=$true
}

#security policy II: parse the data -- i know this seems like bizarre logic but match seems to be a law unto itself
if (!$varNoSecPols) {
    if ($arrSecurityPolicies -match '.VBS') {
        #do nothing
    } else {
        $varFileRisks+="VBS, "
    }
    if ($arrSecurityPolicies -match '.CPL') {
        #do nothing
    } else {
        $varFileRisks+="CPL, "
    }
    if ($arrSecurityPolicies -match '.SCR') {
        #do nothing
    } else {
        $varFileRisks+="SCR, "
    }
    if ($arrSecurityPolicies -match "\u202E") {
        #do nothing
    } else {
        $varFileRisks+="Right-to-Left override"
    }
}

#security policy III: deliver the results
if ($varFileRisks) {
    write-host "- ALERT: The Security Policy does not prohibit execution of problematic file types (https://goo.gl/P6ec8q)."
    write-host "  These file types are: $varFileRisks"
    $varAlerts++
    Write-EventLog -LogName 'Application' -Source 'Security Audit' -EntryType Error -EventID 59120 -Message "Security Audit Alert: The Windows Security Policy is not configured to block files with dangerous extensions from executing.`rThese file types are: $varFileRisks`.`rIn addition, the right-to-left unicode character should also be blocked to mitigate against extension masquerade attacks.`rMore information: https://www.ipa.go.jp/security/english/virus/press/201110/E_PR201110.html"
}

write-host `r
write-host "============================================================================="
if ($varWarnings -ge 1) {
    write-host "- Total warnings: $varWarnings"
}
if ($varAlerts -ge 1) {
    write-host "- Total alerts:   $varAlerts"
}
write-host "============================================================================="
write-host "Security audit completed at $(get-date)"
write-host "You may consider also running the BitLocker audit Component on this device."