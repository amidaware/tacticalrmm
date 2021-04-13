<# 
.SYNOPSIS
   License Windows 10

.DESCRIPTION
   Insert License key into Windows 10 and activate

.NOTES
   For Windows installations in different languages, you will need to edit the following:
   Select-String -Pattern "^License Status:"
   and
   $LicenseStatus -match "Licensed"
   to match your specific language translation.

.FUNCTIONALITY
   PowerShell v3+
#>

if ($Args.Count -eq 0) {
   Write-Output "New Product Key is Required"
   exit 1
}

$param1 = $args[0]

$OSKey = "$param1"
$SLMgr = "C:\Windows\System32\slmgr.vbs"

Write-Output "Inserting license key: $OSKey"
$InsertKey = & cscript $SLMgr /ipk $OSKey
$RetryCount = 3

while ($RetryCount -gt 0) {
   Write-Output "Activating license key..."
   & cscript $SLMgr /ato
    
   Write-Output "Verifying activation status"
   $SLMgrResult = & cscript $SLMgr /dli
   $LicenseStatus = ([string]($SLMgrResult | Select-String -Pattern "^License Status:")).Remove(0, 16)
   if ($LicenseStatus -match "Licensed") {
      Write-Host "Activation Successful" -ForegroundColor Green
      $retryCount = 0
   }
   else {
      Write-Error "Activation failed."
      $RetryCount -= 1
   }
}