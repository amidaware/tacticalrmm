Write-Host "Running Windows Defender Quick Scan in Background" -ForegroundColor Green
Start-MpScan -ScanType QuickScan -AsJob
