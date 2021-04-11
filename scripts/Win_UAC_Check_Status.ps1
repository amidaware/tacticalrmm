$ErrorActionPreference = 'silentlycontinue'
$PSDenabled = (Get-ItemProperty HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System).PromptOnSecureDesktop
$CPAenabled = (Get-ItemProperty HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System).ConsentPromptBehaviorAdmin


if ($PSDenabled -Eq 1 -And $CPAenabled -Eq 5) {
    Write-Output "UAC is Enabled"
    exit 0
}

elseif ($PSDenabled -Eq 1 -And $CPAenabled -Eq 2) {
    Write-Output "UAC is Enabled"
    exit 0
}

else {
    Write-Output "UAC is Disabled"
    exit 1
}


Exit $LASTEXITCODE