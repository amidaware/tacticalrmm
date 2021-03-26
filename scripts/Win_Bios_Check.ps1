## Copied from https://github.com/ThatsNASt/tacticalrmm to add to new pull request for https://github.com/wh1te909/tacticalrmm
#Returns basic information about BIOS
#Test Passed on Windows 7 8 Workstations and Server 2008 

Try {
    $colBios = Get-WmiObject -Class "Win32_BIOS"  
    Foreach ($objBios in $colBios) { 
        $rDate = [System.Management.ManagementDateTimeconverter]::ToDateTime($objBios.ReleaseDate) 
        Write-Host "Status is" $objBios.Status 
        Write-Host "Primary BIOS is" $objBios.PrimaryBIOS 
        Write-Host "SMBIOS BIOS Version is" $objBios.SMBIOSBIOSVersion 
        Write-Host "SMBIOS Major Version is" $objBios.SMBIOSMajorVersion 
        Write-Host "SMBIOS Minor Version is" $objBios.SMBIOSMinorVersion 
        Write-Host "Manufacturer is" $objBios.Manufacturer 
        Write-Host "Release Date is" $rDate
    }
    Write-Host "Script Check passed"
    Exit 0
} 
Catch {
    Write-Host "Script Check Failed"
    Exit 1001
} 
