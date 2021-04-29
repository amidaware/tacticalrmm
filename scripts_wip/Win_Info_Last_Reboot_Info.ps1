
#Find last reboot information

gwmi win32_ntlogevent -filter "LogFile='System' and EventCode='1074' and Message like '%restart%'" | 
    select User,@{n="Time";e={$_.ConvertToDateTime($_.TimeGenerated)}}
	
