## Getting Chrome version

$ResultWow6432 = (Get-ItemProperty HKLM:\Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall\* | Where-Object { $_ -match "Chrome" } | Select-Object -ExpandProperty DisplayVersion)
$Result = (Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\* | Where-Object { $_ -match "Chrome" } | Select-Object -ExpandProperty DisplayVersion)

if ($ResultWow6432) {
    
}
Write-Output "Version Wow6432: $($ResultWow6432)`r"
Write-Output "Version: $($Result)`r"
