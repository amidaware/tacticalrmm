# FAQ


#### How do I do X feature in the web UI?
Alot of features in the web UI are hidden behind right-click menus; almost everything has a right click menu so if you don't see something, try right clicking on it.
#### Where are the linux / mac agents?
Linux / Mac agents are currently under development.

#### I am locked out of the web UI. How do I reset my password?

SSH into your server and run these commands:

!!!note
    The code below will reset the password for the account that was created during install.
    To reset a password for a different user, you should use the web UI (see the next question below), but can also do so through the command line by replacing<br/>
    `user = User.objects.first()`<br/>
    with<br/>
    `user = User.objects.get(username='someuser')`
    <br/>
    in the code snippet below.


```python
tactical@tacrmm:~$ /rmm/api/env/bin/python /rmm/api/tacticalrmm/manage.py shell
Python 3.9.2 (default, Feb 21 2021, 00:50:28)
[GCC 9.3.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
(InteractiveConsole)
>>> from accounts.models import User
>>> user = User.objects.first()
>>> user.set_password("superSekret123")
>>> user.save()
>>> exit()
```

<br/>

#### How do I reset password or 2 factor token?
From the web UI, click **Settings > User Administration** and then right-click on a user:<br/><br/>
![reset2fa](images/reset2fa.png)
<br/><br/>
Or from the command line:<br/>
```python
tactical@tacrmm:~$ /rmm/api/env/bin/python /rmm/api/tacticalrmm/manage.py shell
Python 3.9.2 (default, Feb 21 2021, 00:50:28)
[GCC 9.3.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
(InteractiveConsole)
>>> from accounts.models import User
>>> user = User.objects.get(username='someuser')
>>> user.totp_key = None
>>> user.save(update_fields=['totp_key'])
>>> exit()
```
<br/>
Then simply log out of the web UI and next time the user logs in they will be redirected to the 2FA setup page which will present a barcode to be scanned with the Authenticator app.
