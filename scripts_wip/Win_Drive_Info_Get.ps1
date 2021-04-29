###
# Author: Dave Long <dlong@cagedata.com>
# Gets a list of all mount points and what type of drive the
# mount point is stored on
###

# Get all of the physical disks attached to system
$Partitions = Get-Partition | Where-Object { [string]($_.DriveLetter) -ne "" }

$Output = @()

$Partitions | ForEach-Object {
  $Disk = Get-PhysicalDisk -DeviceNumber $_.DiskNumber
  $Output += [PSCustomObject]@{
    MountPoint = $_.DriveLetter
    DiskType = $Disk.MediaType
    DriveName = $Disk.FriendlyName
    DriveSerialNumber = $Disk.SerialNumber
    SizeInGigabytes = $Disk.Size/1GB
    Health = $Disk.HealthStatus
    SystemDrive = $env:SystemDrive[0] -eq $_.DriveLetter ? $true : $false
  }
}

$Output | Format-Table