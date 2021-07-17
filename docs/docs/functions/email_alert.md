# Email Setup

Under **Settings > Global Settings > Email Alerts**

## Setting up Tactical RMM Alerts using Open Relay

MS 365 in this example

1. Log into Tactical RMM
2. Go to Settings
3. Go to Global Settings
4. Click on Alerts
5. Enter the email address (or addresses) you want to receive alerts to eg info@mydomain.com
6. Enter the from email address (this will need to be part of your domain on 365, however it doesn’t need a license) eg rmm@mydomain.com
7. Go to MXToolbox.com and enter your domain name in, copy the hostname from there and paste into Host
8. Change the port to 25
9. Click Save
10. Login to admin.microsoft.com
11. Go to Exchange Admin Centre
12. Go to “Connectors” under “Mail Flow”
13. Click to + button
14. In From: select “Your organisations email server”
15. In To: select “Office 365”
16. Click Next
17. In the Name type in RMM
18. Click By Verifying that the IP address……
19. Click +
20. Enter your IP and Click OK
21. Click Next
22. Click OK

## Setting up Tactical RMM Alerts using username & password

Gmail in this example

1. Log into Tactical RMM
2. Go to Settings
3. Go to Global Settings
4. Click on Alerts
5. Enter the email address (or addresses) you want to receive alerts to eg info@mydomain.com
6. Enter the from email address myrmm@gmail.com
7. Tick the box “My server requires Authentication”  
8. Enter your username e.g. myrmm@gmail.com
9. Enter your password
10. Change the port to 587
11. Click Save
