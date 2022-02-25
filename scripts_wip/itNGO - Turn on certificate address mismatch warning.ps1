Write-Output "Enabling certificate address mismatch warning ..."

$registryPath = "HKLM:\Software\Policies\Microsoft\Windows\CurrentVersion\Internet Settings"

$Name = "WarnOnBadCertRecving"

$value = "00000001"

$Type = "DWORD"

IF(!(Test-Path $registryPath))

  {

    New-Item -Path $registryPath -Force | Out-Null

    New-ItemProperty -Path $registryPath -Name $name -Value $value -PropertyType $Type -Force | Out-Null}

 ELSE {

    New-ItemProperty -Path $registryPath -Name $name -Value $value -PropertyType $Type -Force | Out-Null}

Write-Output "Done... bye"