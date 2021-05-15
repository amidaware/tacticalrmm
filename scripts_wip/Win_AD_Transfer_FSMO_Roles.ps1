<#
    .SYNOPSIS
    I do this

    .DESCRIPTION 
    I really do a lot of this

    .OUTPUTS
    Results are printed to the console. Future releases will support outputting to a log file. 

    .NOTES
    Change Log
    V1.0 Initial release

    Reference Links: www.google.com
#>

# Transfer FSMO Roles to server
# Make this machine the FSMO  Master role.

Move-ADDirectoryServerOperationMasterRole -Identity $env:computername -OperationMasterRole pdcemulator, ridmaster, infrastructuremaster, schemamaster, domainnamingmaster -Force