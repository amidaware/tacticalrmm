#Windows Defender Exclusions for Tactical
Add-MpPreference -ExclusionPath 'C:\Program Files\TacticalAgent\*'
Add-MpPreference -ExclusionPath 'C:\Windows\Temp\winagent-v*.exe'
Add-MpPreference -ExclusionPath 'C:\Program Files\Mesh Agent\*'
