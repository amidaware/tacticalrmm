## Update this script for your company, Modify the "mail variables" section
## Also, host BlueScreenView.exe on a website and update the $url variable
## location accordingly
##
## Blue Screen View is available as freeware at
##  https://www.nirsoft.net/utils/blue_screen_view.html


###script variables
 $scriptName = "Blue Screen View"
 $computerName = (get-wmiObject win32_computersystem).name
 $computerDomain = (get-wmiObject win32_computersystem).domain
 if($computerdomain -notlike '*.*'){ #if there's no period in the domain, (workgroup)
	$computerDomain = "$computerDomain.local"	
 }

###mail variables
 $smtpServer = 'mail.server.com'
 $smtpPort = '25'
 $smtpFrom = "Atera-$computername@$computerdomain"
 $smtpTo = 'support@YOURDOMAIN.com'
 $messageSubject = "Atera Script: $computerName, $scriptName"
 $attachment = "c:\windows\temp\crashes.html"
 $messageBody += "----See Attachment----"

###script start
 $messageBody = "----Blue Screen View Results----`r`n"
 $url = "https://YOURDOMAIN.com/files/BlueScreenView.exe"
 $filename = "BlueScreenView.exe"
 $client = New-Object System.Net.WebClient
 $client.DownloadFile($url, "$env:temp\$filename")
 Start-Process -FilePath "$env:temp\$filename" -ArgumentList "/shtml","c:\Windows\temp\crashes.html","/sort 2","/sort ~1"""

###send mail
 Send-MailMessage -Port $smtpPort -SmtpServer $smtpServer -From $smtpFrom -To $smtpTo -Subject $messageSubject -Body $messageBody -Attachments $attachment