Write-Host "Running Windows Defender Full Scan in Background" -ForegroundColor Green
Start-MpScan -ScanPath C:\ -ScanType FullScan -AsJob