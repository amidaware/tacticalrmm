# From nullzilla

# Requires -Version 3.0
# Requires -RunAsAdministrator
 
# If this is a virtual machine, we don't need to continue
$Computer = Get-CimInstance -ClassName 'Win32_ComputerSystem'
if ($Computer.Model -like 'Virtual*') {
    exit
}
 
$disks = (Get-CimInstance -Namespace 'Root\WMI' -ClassName 'MSStorageDriver_FailurePredictStatus' | Select-Object 'InstanceName')
 
$Warnings = @()
 
foreach ($disk in $disks.InstanceName) {
    # Retrieve SMART data
    $SmartData = (Get-CimInstance -Namespace 'Root\WMI' -ClassName 'MSStorageDriver_ATAPISMartData' | Where-Object 'InstanceName' -eq $disk)
 
    [Byte[]]$RawSmartData = $SmartData | Select-Object -ExpandProperty 'VendorSpecific'
    
    # Starting at the third number (first two are irrelevant)
    # get the relevant data by iterating over every 12th number
    # and saving the values from an offset of the SMART attribute ID
    [PSCustomObject[]]$Output = for ($i = 2; $i -lt $RawSmartData.Count; $i++) {
        if (0 -eq ($i - 2) % 12 -and $RawSmartData[$i] -ne 0) {
            # Construct the raw attribute value by combining the two bytes that make it up
            [Decimal]$RawValue = ($RawSmartData[$i + 6] * [Math]::Pow(2, 8) + $RawSmartData[$i + 5])
 
            $InnerOutput = [PSCustomObject]@{
                DiskID   = $disk
                ID       = $RawSmartData[$i]
                #Flags    = $RawSmartData[$i + 1]
                #Value    = $RawSmartData[$i + 3]
                Worst    = $RawSmartData[$i + 4]
                RawValue = $RawValue
            }
 
            $InnerOutput
        }
    }
    
    # Reallocated Sectors Count
    $Warnings += $Output | Where-Object ID -eq 5 | Where-Object RawValue -gt 1 | Format-Table
 
    # Spin Retry Count
    $Warnings += $Output | Where-Object ID -eq 10 | Where-Object RawValue -ne 0 | Format-Table
 
    # Recalibration Retries 
    $Warnings += $Output | Where-Object ID -eq 11 | Where-Object RawValue -ne 0 | Format-Table
 
    # Used Reserved Block Count Total
    $Warnings += $Output | Where-Object ID -eq 179 | Where-Object RawValue -gt 1 | Format-Table
 
    # Erase Failure Count
    $Warnings += $Output | Where-Object ID -eq 182 | Where-Object RawValue -ne 0 | Format-Table
 
    # SATA Downshift Error Count or Runtime Bad Block
    $Warnings += $Output | Where-Object ID -eq 183 | Where-Object RawValue -ne 0 | Format-Table
 
    # End-to-End error / IOEDC
    $Warnings += $Output | Where-Object ID -eq 184 | Where-Object RawValue -ne 0 | Format-Table
 
    # Reported Uncorrectable Errors
    $Warnings += $Output | Where-Object ID -eq 187 | Where-Object RawValue -ne 0 | Format-Table
 
    # Command Timeout
    $Warnings += $Output | Where-Object ID -eq 188 | Where-Object RawValue -gt 2 | Format-Table
 
    # High Fly Writes
    $Warnings += $Output | Where-Object ID -eq 189 | Where-Object RawValue -ne 0 | Format-Table
 
    # Temperature Celcius
    $Warnings += $Output | Where-Object ID -eq 194 | Where-Object RawValue -gt 50 | Format-Table
 
    # Reallocation Event Count
    $Warnings += $Output | Where-Object ID -eq 196 | Where-Object RawValue -ne 0 | Format-Table
 
    # Current Pending Sector Count
    $Warnings += $Output | Where-Object ID -eq 197 | Where-Object RawValue -ne 0 | Format-Table
 
    # Uncorrectable Sector Count
    $Warnings += $Output | Where-Object ID -eq 198 | Where-Object RawValue -ne 0 | Format-Table
 
    # UltraDMA CRC Error Count
    $Warnings += $Output | Where-Object ID -eq 199 | Where-Object RawValue -ne 0 | Format-Table
 
    # Soft Read Error Rate
    $Warnings += $Output | Where-Object ID -eq 201 | Where-Object Worst -lt 95 | Format-Table
 
    # SSD Life Left
    $Warnings += $Output | Where-Object ID -eq 231 | Where-Object Worst -lt 50 | Format-Table
 
    # SSD Media Wear Out Indicator
    $Warnings += $Output | Where-Object ID -eq 233 | Where-Object Worst -lt 50 | Format-Table
 
}
 
$Warnings += Get-CimInstance -Namespace 'Root\WMI' -ClassName 'MSStorageDriver_FailurePredictStatus' |
Select-Object InstanceName, PredictFailure, Reason |
Where-Object { $_.PredictFailure -ne $False } | Format-Table
 
$Warnings += Get-CimInstance -ClassName 'Win32_DiskDrive' |
Select-Object Model, SerialNumber, Name, Size, Status |
Where-Object { $_.status -ne 'OK' } | Format-Table
 
$Warnings += Get-PhysicalDisk |
Select-Object FriendlyName, Size, MediaType, OperationalStatus, HealthStatus |
Where-Object { $_.OperationalStatus -ne 'OK' -or $_.HealthStatus -ne 'Healthy' } | Format-Table
 
if ($Warnings) {
    $Warnings = $warnings | Out-String
    $Warnings
    Write-Host "$Warnings"
    Exit 1
}
 
if ($Error) {
    if ($Error -match "Not supported") {
        $notsup = "You may need to switch from ACHI to RAID/RST mode, see the link for how to do this non-destructively: https://www.top-password.com/blog/switch-from-raid-to-ahci-without-reinstalling-windows/"
        $notsup
    }
    Write-Host "$Error $notsup"
    exit 1
}
 
