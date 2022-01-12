#Uses RunAsUser and BurntToast to display a popup message to the currently logged on user, alerting that their password is expiring.
#Accepts all arguments as the message text or can quote with 'your message here' if using special characters in the message.
#Optional: C:\Program Files\TacticalAgent\BurntToastLogo.png will be displayed if the file exists. Image dimensions 478px (W) x 236px (H)
#BurntToast Module Source and Examples: https://github.com/Windos/BurntToast
#RunAsUser Module Source and Examples: https://github.com/KelvinTegelaar/RunAsUser

# Assign last logged in user from TRMM to variable
param (
  [string] $lastLoggedIn
)

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# Check for, and install pre-reqs if not found.
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

# Check to confirm temporary directory is present, and if not, create.
$directoryPath = "C:\ProgramData\TRMM\temp"
if(!(test-path $directoryPath))
{
      New-Item -ItemType Directory -Force -Path $directoryPath
}

# Get password expiration date with NET USER command.  If returned output is null, then run command again for local user.
$output = net user $lastLoggedIn /domain | find 'Password expires'
if ($output -eq $null)
{
    $output = net user $lastLoggedIn | find 'Password expires'
}

# Parse output to only show expiration date
$passwordExpiry = $output -replace ".*  "

# TESTING - UNCOMMENT AND MANUALLY SET PASSWORD EXPIRY TO TEST SCRIPT AND ALERTS
# $passwordExpiry = "1/14/2022 12:00:00"

# Check if password is set to never expire.
if ($passwordExpiry -eq "Never")
{
    Write-Output "Password is set to never expire.  Exiting."
    Start-Sleep -Seconds 1
    Exit
}
    else
{
    # Calculate time until password expires
    $expiryDetails = ((get-date $passwordExpiry) - (get-date))

    #Strip out the number of days until password expires
    $expiryDays = $expiryDetails.Days
}

# Set messagetext variable depending on how soon the password expires.
if ($expiryDays -eq 7)
{
    $messagetext = "Your password will expire in 7 days or less.  You should consider changing your password."
    $urgentFlag = 0
}

if ($expiryDays -eq 3)
{
    $messagetext = "Your password will expire in 3 days or less.  Please change your password."
    $urgentFlag = 0
}

if ($expiryDays -eq 2)
{
    $messagetext = "Your password will expire in 2 days or less.  It is important that you change your password as soon as possible."
    $urgentFlag = 0
}

if ($expiryDays -eq 1)
{
    $messagetext = "Your password is going to expire!  To ensure you are not blocked from logging into your PC or online services, you must update your password immediately."
    $urgentFlag = 1
}


# Check if URGENT BurntToastLogo.png file is required and download appropriate image.
if ($urgentFlag -eq 1)
{
    Write-Output "Downloading URGENT Logo"
    $urgentDownloadPath = "https://YOURDOMAIN.COM/BurntToastLogoUrgent.png"
    Invoke-WebRequest $urgentDownloadPath -OutFile "C:\Program Files\TacticalAgent\BurntToastLogo.png"
}
else
{
    Write-Output "Downloading Regular Logo"
    $regDownloadPath = "https://YOURDOMAIN.COM/BurntToastLogo.png"
    Invoke-WebRequest $regDownloadPath -OutFile "C:\Program Files\TacticalAgent\BurntToastLogo.png"
}

# Write message text to file on disk
Set-Content -Path c:\ProgramData\TRMM\temp\message.txt -Value $messagetext

# If password expires within either 7, 3, 2, or 1 days, send popup to user.
if ($expiryDays -eq 7 -or $expiryDays -eq 3 -or $expiryDays -eq 2 -or $expiryDays -eq 1)
{

    Invoke-AsCurrentUser -scriptblock {

        $messageContent = Get-Content -Path c:\ProgramData\TRMM\temp\message.txt
        $heroimage = New-BTImage -Source 'C:\Program Files\TacticalAgent\BurntToastLogo.png' -HeroImage
        $Text1 = New-BTText -Content "*** IMPORTANT Alert from IT Department ***"
        $Text2 = New-BTText -Content "$messageContent"
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
    Remove-Item -Path C:\ProgramData\TRMM\temp\message.txt

}
    else
{
    Write-Output "Password alert for $lastLoggedIn does not need to be triggered.  Exiting."
    Start-Sleep -Seconds 1
    Exit    
}