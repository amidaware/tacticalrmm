## Copied from https://github.com/ThatsNASt/tacticalrmm to add to new pull request for https://github.com/wh1te909/tacticalrmm
#
# WARNING
# 1. Only applies to drive C
# 2. Assumes you're encrypting more than the used space. "Used Space Only Encrypted" is the default windows behavior which is not compatible here.

function Log-Message {
    Param
    (
        [Parameter(Mandatory = $true, Position = 0)]
        [string]$LogMessage,
        [Parameter(Mandatory = $false, Position = 1)]
        [string]$LogFile,
        [Parameter(Mandatory = $false, Position = 2)]
        $Echo
    )
    if ($LogFile) {
        Write-Output ("{0} - {1}" -f (Get-Date), $LogMessage) | Out-File -Append $LogFile
        if ($Echo) {
            Write-Output ("{0} - {1}" -f (Get-Date), $LogMessage)
        }
    }
    Else {
        Write-Output ("{0} - {1}" -f (Get-Date), $LogMessage)
    }
}
$log = "BitlockerReport.txt"

#Find BL info
$mbde = [string](manage-bde -status C:)
$mbdeProt = (manage-bde -protectors -get c: | Select-Object -Skip 6)
#Dig out the recovery password, check for PIN
ForEach ($line in $mbdeProt) {
    if ($line -like "******-******-******-******-******-******-******-******") {
        $RecoveryPassword = $line.Trim()
    }
    if ($line -like "*TPM And PIN:*") {
        $PIN = $true
    }
}
#Determine BL status
if ($mbde.Contains("Fully Decrypted")) {
    $Encrypted = "No"
}
if ($mbde.Contains("Fully Encrypted")) {
    $Encrypted = "Yes"
}
if ($mbde.Contains("Encryption in Progress")) {
    $Encrypted = "InProgress"
}
if ($mbde.Contains("Decryption in Progress")) {
    $Encrypted = "InProgressNo"
}

#Check for recovery password, report if found.
if ($RecoveryPassword) {
    Try {
        Log-Message "RP: $RecoveryPassword" $log e -ErrorAction Stop
    }
    #Catch for recovery password in place but encryption not active
    Catch {
        Log-Message "Could not retrieve recovery password, but it is enabled." $log e
    }
}
if (!$RecoveryPassword) {
    Log-Message "No Recovery Password found." $log e
}

#Try to make a summary for common situations
if ($Encrypted -eq "No" -and !$RecoveryPassword) {
    Log-Message "WARNING: Decrypted, no password." $log e
    exit 2001
}
if ($Encrypted -eq "No" -and $RecoveryPassword) {
    Log-Message "WARNING: Decrypted, password set. Interrupted process?" $log e
    exit 2002
}
if ($Encrypted -eq "Yes" -and !$RecoveryPassword) {
    Log-Message "WARNING: Encrypted, no password." $log e
    exit 2000
}
if ($Encrypted -eq "InProgress" -and $RecoveryPassword) {
    Log-Message "WARNING: Encryption in progress, password set." $log e
    exit 3000
}
if ($Encrypted -eq "InProgress" -and !$RecoveryPassword) {
    Log-Message "WARNING: Encryption in progress, no password." $log e
    exit 3001
}
if ($Encrypted -eq "InProgressNo") {
    Log-Message "WARNING: Decryption in progress" $log e
    exit 3002
}
if ($Encrypted -eq "Yes" -and $RecoveryPassword -and !$PIN) {
    Log-Message "WARNING: Encrypted, PIN DISABLED, password is set." $log e
    exit 3003
}
if ($Encrypted -eq "Yes" -and $RecoveryPassword -and $PIN -eq $true) {
    Log-Message "SUCCESS: Encrypted, PIN enabled, password is set." $log e
    Write-Host "Script check passed"
    exit 0
}
