# This script will check if a specific proces is running, and if its not it will try and run it.
# Can be altered to be run as logged in user, as already written in the script. If you need to run it as SYSTEM, just remove
# RunAsUser block. This example tries to find 3 processes running in memory. If they are not found, script will run them.
# Edit process names as needed.

install-module RunAsUser

$scriptblock = {

$path1 = "c:\metaline\run\metalink.exe"
$path2 = "c:\metaline\run\metalink_sg_fp600.exe"
$path3 = "c:\fpserver\fpserver.exe"

If (Test-Path -Path $path1 ) {
  if((Get-Process -Name metalink -ErrorAction SilentlyContinue) -eq $null){
    ."C:\Metaline\Run\Metalink.exe"
  }
}

If (Test-Path -Path $path2 ) {
  if((Get-Process -Name metalink_sg_fp600 -ErrorAction SilentlyContinue) -eq $null){
    ."c:\metaline\run\metalink_sg_fp600.exe"
  }
}

If (Test-Path -Path $path3 ) {
  if((Get-Process -Name fpserver -ErrorAction SilentlyContinue) -eq $null){
    ."c:\fpserver\fpserver.exe"
  }
}
}

invoke-ascurrentuser -scriptblock $scriptblock -NoWait