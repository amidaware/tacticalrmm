# Add a task to Task Scheduler

$Trigger = New-ScheduledTaskTrigger -At 10:00am –Daily # Specify the trigger settings
$User = "NT AUTHORITY\SYSTEM" # Specify the account to run the script
$Action = New-ScheduledTaskAction -Execute "PowerShell.exe" -Argument "YOUR COMMAND HERE" # Specify what program to run and with its parameters
Register-ScheduledTask -TaskName "SomeTaskName" -Trigger $Trigger -User $User -Action $Action -RunLevel Highest –Force # Specify the name of the task