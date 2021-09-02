# Checking for insecure by design print features being enabled
# See https://support.microsoft.com/en-us/topic/kb5005010-restricting-installation-of-new-printer-drivers-after-applying-the-july-6-2021-updates-31b91c02-05bc-4ada-a7ea-183b129578a7

$PointAndPrintNoElevation = (Get-ItemProperty -Path "HKLM:\Software\Policies\Microsoft\Windows NT\Printers\PointAndPrintNoElevation").NoWarningNoElevationOnInstall
$PointAndPrintUpdatePrompt = (Get-ItemProperty -Path "HKLM:\Software\Policies\Microsoft\Windows NT\Printers\PointAndPrintNoElevation").UpdatePromptSettings

if ($PointAndPrintNoElevation -Eq 1) {
    Write-Output "Point and Print WarningNoElevationOnInstall set to true. WARNING: You are insecure-by-design."
    exit 1
}

elseif ($PointAndPrintUpdatePrompt -Eq 1) {
    Write-Output "Point and Print PointAndPrintUpdatePrompt set to true. WARNING: You are insecure-by-design."
    exit 1
}

else {
    Write-Output "WarningNoElevationOnInstall UpdatePromptSettings set to false. No vulnerabilities"
    exit 0
}

Exit $LASTEXITCODE