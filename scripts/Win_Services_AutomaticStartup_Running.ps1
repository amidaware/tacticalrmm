###
# Author: Dave Long <dlong@cagedata.com>
# Date: 2021-05-12
#
# Gets a list of all services that should be running (startup type is automatic),
# but are currently not running and optionally tries to start them.
###

# To not automatically try to start all non-running automatic services
# change the following variable value to $false

$AutoStart = $true

$Services = Get-Service | `
    Where-Object { $_.StartType -eq "Automatic" -and $_.Status -ne "Running" }

$Services | Format-Table

if ($AutoStart) { $Services | Start-Service }
