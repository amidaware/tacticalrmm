# From gretsky
# https://discord.com/channels/736478043522072608/744282073870630912/891008070434558042

$CIMTriggerClass = Get-CimClass -ClassName MSFT_TaskEventTrigger -Namespace Root/Microsoft/Windows/TaskScheduler:MSFT_TaskEventTrigger
$Trigger = New-CimInstance -CimClass $CIMTriggerClass -ClientOnly
$Trigger.Subscription = "<QueryList><Query Id='0' Path='Microsoft-Windows-WLAN-AutoConfig/Operational'><Select Path='Microsoft-Windows-WLAN-AutoConfig/Operational'>*[System[Provider[@Name='Microsoft-Windows-WLAN-AutoConfig'] and EventID=11001]]</Select></Query></QueryList>"
$Trigger.Enabled = $True 
$Taskname = 'TacticalRMM_TASKID'
Set-ScheduledTask -TaskName $Taskname -Trigger $Trigger