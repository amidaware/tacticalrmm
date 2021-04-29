# Transfer FSMO Roles to server
# Make this machine the FSMO  Master role.

Move-ADDirectoryServerOperationMasterRole -Identity $env:computername -OperationMasterRole pdcemulator,ridmaster,infrastructuremaster,schemamaster,domainnamingmaster -Force