

$Source = "$downloadurl"
$SourceDownloadLocation = "C:\temp\Dell_Command_Update_4.3"
$SourceInstallFile = "$SourceDownloadLocation\DCU_Setup_4_3_0.exe"
$ProgressPreference = 'SilentlyContinue'

If (Test-Path -Path $SourceInstallFile -PathType Leaf) {
    
  $proc = Start-Process "$SourceInstallFile" -ArgumentList "/s" -PassThru
  Wait-Process -InputObject $proc
  if ($proc.ExitCode -ne 0) {
    Write-Warning "Exited with error code: $($proc.ExitCode)"
  }
  else {
    Write-Output "Successful install with exit code: $($proc.ExitCode)"
  }


}
else {

  New-Item -Path $SourceDownloadLocation -ItemType directory
  Invoke-WebRequest $Source -OutFile $SourceInstallFile

  $proc = Start-Process "$SourceInstallFile" -ArgumentList "/s" -PassThru
  Wait-Process -InputObject $proc
  if ($proc.ExitCode -ne 0) {
    Write-Warning "Exited with error code: $($proc.ExitCode)"
  }
  else {
    Write-Output "Successful install with exit code: $($proc.ExitCode)"
  }
}