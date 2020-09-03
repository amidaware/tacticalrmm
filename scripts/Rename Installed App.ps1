$NewAgentName = $args[0]

$AgentName = (Get-ItemProperty "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\{0D34D278-5FAF-4159-A4A0-4E2D2C08139D}_is1").DisplayName
if ($AgentName -ne "$NewAgentName") {
    Set-ItemProperty -Name DisplayName -Path "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\{0D34D278-5FAF-4159-A4A0-4E2D2C08139D}_is1" -Value $NewAgentName
    $AgentName = (Get-ItemProperty "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\{0D34D278-5FAF-4159-A4A0-4E2D2C08139D}_is1").DisplayName
    if ($AgentName -ne $NewAgentName) {
        exit 1
    } else {
        exit 0
    }
}
