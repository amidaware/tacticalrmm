# Path for the workdir
if ( Test-Path -Path "$env:LOCALAPPDATA\Microsoft\OneDrive\OneDrive.exe" -PathType Leaf ) {
    $workdir = "$env:LOCALAPPDATA\Microsoft\OneDrive"
} elseif  ( Test-Path -Path "C:\Program Files (x86)\Microsoft\OneDrive\OneDrive.exe" -PathType Leaf ) {
    $workdir = "C:\Program Files (x86)\Microsoft\OneDrive"
} else {
    Write-Host "OneDrive is not installed"
}

# Start-Process of clearing OneDrive cache
$p = Start-Process -FilePath $workdir'\OneDrive.exe' -ArgumentList '/reset' -NoNewWindow -Wait -PassThru
$p.ExitCode
Write-Host "OneDrive Cache has been cleared."

# Restart OneDrive
$p = Start-Process -FilePath $workdir'\OneDrive.exe' -NoNewWindow -Wait -PassThru
$p.ExitCode