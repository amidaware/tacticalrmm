# gretsky https://discord.com/channels/736478043522072608/744281869499105290/890996626716508180
# remove non domain joined device from trmm and unjoin them from Azure Ad

$domain = (Get-WmiObject -Class win32_computersystem -ComputerName localhost).domain
if ($domain.toupper().contains('DOMAIN')) {
    Write-Output 'DOMAIN OK'
}
else {
    $ChkReg = Test-Path 'HKLM:\SOFTWARE\TacticalRMM\'
    If ($ChkReg -eq $True) {
        $regrmm = Get-ItemProperty -Path HKLM:\SOFTWARE\TacticalRMM\        
        & 'C:\Program Files\TacticalAgent\unins000.exe' /VERYSILENT
        start-sleep -s 20
    }
    dsregcmd.exe /debug /leave
    $Location = 'hklm:\SOFTWARE\Policies\Microsoft\Windows\WorkplaceJoin'
 
    if ( !(Test-Path $Location) ) {
        New-item -path $Location
        New-ItemProperty -Path $Location -Name "BlockAADWorkplaceJoin" -PropertyType Dword -Value "1"
    }
    
    Start-Sleep -s 20
    exit 0
}