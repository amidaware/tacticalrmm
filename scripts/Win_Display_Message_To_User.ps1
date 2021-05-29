#Uses RunAsUser and BurntToast to display a popup message to the currently logged on user.
#Accepts all arguments as the message text or can quote with 'your message here' if using special characters in the message.
#Optional: C:\Program Files\TacticalAgent\BurntToastLogo.png will be displayed if the file exists. Image dimensions 478px (W) x 236px (H)
#BurntToast Module Source and Examples: https://github.com/Windos/BurntToast
#RunAsUser Module Source and Examples: https://github.com/KelvinTegelaar/RunAsUser


[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

if (Get-PackageProvider -Name NuGet) {
    #Write-Host "NuGet Already Added"
} 
else {
    Write-Host "Installing NuGet"
    Install-PackageProvider -Name NuGet -Force
} 

if (Get-Module -ListAvailable -Name BurntToast) {
    #Write-Host "BurntToast Already Installed"
} 
else {
    Write-Host "Installing BurntToast"
    Install-Module -Name BurntToast -Force
}
 
if (Get-Module -ListAvailable -Name RunAsUser) {
    #Write-Host "RunAsUser Already Installed"
} 
else {
    Write-Host "Installing RunAsUser"
    Install-Module -Name RunAsUser -Force
}

# Used to pull variables in and use them inside the script block. Contains message to show user
Set-Content -Path c:\windows\temp\message.txt -Value $args

Invoke-AsCurrentUser -scriptblock {
 
    $messagetext = Get-Content -Path c:\windows\temp\message.txt
    $heroimage = New-BTImage -Source 'C:\Program Files\TacticalAgent\BurntToastLogo.png' -HeroImage
    $Text1 = New-BTText -Content  "Message from IT"
    $Text2 = New-BTText -Content "$messagetext"
    $Button = New-BTButton -Content "Snooze" -snooze -id 'SnoozeTime'
    $Button2 = New-BTButton -Content "Dismiss" -dismiss
    $5Min = New-BTSelectionBoxItem -Id 5 -Content '5 minutes'
    $10Min = New-BTSelectionBoxItem -Id 10 -Content '10 minutes'
    $1Hour = New-BTSelectionBoxItem -Id 60 -Content '1 hour'
    $4Hour = New-BTSelectionBoxItem -Id 240 -Content '4 hours'
    $1Day = New-BTSelectionBoxItem -Id 1440 -Content '1 day'
    $Items = $5Min, $10Min, $1Hour, $4Hour, $1Day
    $SelectionBox = New-BTInput -Id 'SnoozeTime' -DefaultSelectionBoxItemId 10 -Items $Items
    $action = New-BTAction -Buttons $Button, $Button2 -inputs $SelectionBox
    $Binding = New-BTBinding -Children $Text1, $Text2 -HeroImage $heroimage
    $Visual = New-BTVisual -BindingGeneric $Binding
    $Content = New-BTContent -Visual $Visual -Actions $action
    Submit-BTNotification -Content $Content
}

# Cleanup temp file for message variables
Remove-Item -Path c:\windows\temp\message.txt
