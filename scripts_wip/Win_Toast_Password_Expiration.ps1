#Uses RunAsUser and BurntToast to display a popup message to the currently logged on user, alerting that their password is expiring.
#Accepts all arguments as the message text or can quote with 'your message here' if using special characters in the message.
#Optional: C:\Program Files\TacticalAgent\BurntToastLogo.png will be displayed if the file exists. Image dimensions 478px (W) x 236px (H)
#BurntToast Module Source and Examples: https://github.com/Windos/BurntToast
#RunAsUser Module Source and Examples: https://github.com/KelvinTegelaar/RunAsUser


# Set parameters
param (
  [int[]] $expiryDaysToAlert=@(1,2,3,7)
)


# Will exit when a user is not logged in
try{
  $loggedInUser = ((Get-WMIObject -ClassName Win32_ComputerSystem).Username).Split('\')[1]
}catch{
   Write-Host "No logged in user.  Exiting"
   Exit 0
}


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


# Get password expiration date with NET USER command.  If returned output is null, then run command again for local user.
$output = net user $LoggedInUser /domain | find 'Password expires'
if ($output -eq $null)
{
    $output = net user $LoggedInUser | find 'Password expires'
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
if ($expiryDays -le 1)
{
    $messagetext = "Your password is going to expire!  To ensure you are not blocked from logging into your PC or online services, you must update your password immediately."
    $urgentFlag = 1
}
elseif ($expiryDays -le 2)
{
    $messagetext = "Your password will expire in 2 days or less.  It is important that you change your password as soon as possible."
    $urgentFlag = 0
}
elseif ($expiryDays -le 3)
{
    $messagetext = "Your password will expire in 3 days or less.  Please change your password."
    $urgentFlag = 0
}
elseif ($expiryDays -le 7)
{
    $messagetext = "Your password will expire in 7 days or less.  You should consider changing your password."
    $urgentFlag = 0
}


# Download Regular and Urgent Image files
$regDownloadPath = "https://YOURDOMAIN.COM/BurntToastLogo.png"
Invoke-WebRequest $regDownloadPath -OutFile "C:\Program Files\TacticalAgent\BurntToastLogo.png"
$urgentDownloadPath = "https://YOURDOMAIN.COM/BurntToastLogoUrgent.png"
Invoke-WebRequest $urgentDownloadPath -OutFile "C:\Program Files\TacticalAgent\BurntToastLogoUrgent.png"


# Check if URGENT BurntToastLogo.png file is required and set variable path
if ($urgentFlag -eq 1)
{
    $popupImage = "C:\Program Files\TacticalAgent\BurntToastLogoUrgent.png"
}
else
{
    $popupImage = "C:\Program Files\TacticalAgent\BurntToastLogo.png"
}


# If password expires is in $expiryDaystAlert days, send popup to user.
if ($expiryDays -in $expiryDaysToAlert)
{
    $command = @"
        `$HeroImage = New-BTImage -Source "${popupImage}" -HeroImage
        `$Text1 = New-BTText -Content "*** IMPORTANT Alert from IT Department ***"
        `$Text2 = New-BTText -Content "${messagetext}"
        `$Button = New-BTButton -Content "Snooze" -snooze -id 'SnoozeTime'
        `$Button2 = New-BTButton -Content "Dismiss" -dismiss
        `$5Min = New-BTSelectionBoxItem -Id 5 -Content '5 minutes'
        `$10Min = New-BTSelectionBoxItem -Id 10 -Content '10 minutes'
        `$1Hour = New-BTSelectionBoxItem -Id 60 -Content '1 hour'
        `$4Hour = New-BTSelectionBoxItem -Id 240 -Content '4 hours'
        `$1Day = New-BTSelectionBoxItem -Id 1440 -Content '1 day'
        `$Items = `$5Min, `$10Min, `$1Hour, `$4Hour, `$1Day
        `$SelectionBox = New-BTInput -Id 'SnoozeTime' -DefaultSelectionBoxItemId 10 -Items `$Items
        `$Action = New-BTAction -Buttons `$Button, `$Button2 -inputs `$SelectionBox
        `$Binding = New-BTBinding -Children `$Text1, `$Text2 -HeroImage `$HeroImage
        `$Visual = New-BTVisual -BindingGeneric `$Binding
        `$Audio = New-BTAudio -Source ms-winsoundevent:Notification.Looping.Alarm4
        `$Content = New-BTContent -Visual `$Visual -Actions `$Action -Audio `$Audio
        Submit-BTNotification -Content `$Content
"@
    
    $scriptblock = [scriptblock]::Create($command)
    Invoke-AsCurrentUser -ScriptBlock $scriptblock

}
    else
{
    Write-Output "Password alert for $lastLoggedIn does not need to be triggered.  Exiting."
    Start-Sleep -Seconds 1
    Exit    
}