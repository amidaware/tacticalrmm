# Updating the RMM

!!!danger
    Do __not__ attempt to manually edit the update script or any configuration files unless specifically told to by one of the developers.<br/><br/>
    Since this software is completely self hosted and we have no access to your server, we have to assume you have not made any config changes to any of the files or services on your server, and the update script will assume this.<br/><br/>
    You should also **never** attempt to automate running the update script via cron.<br/><br/>
    The update script will update itself if needed to the latest version when you run it, and them prompt you to run it again.<br/><br/>
    Sometimes, manual intervention will be required during an update in the form of yes/no prompts, so attempting to automate this will ignore these prompts and cause your installation to break.

SSH into your server as the linux user you created during install.<br/><br/>
__Never__ run any update scripts or commands as the `root` user.<br/>This will mess up permissions and break your installation.<br/><br/>
Download the update script and run it:<br/>
```bash
tactical@tacrmm:~$ wget https://raw.githubusercontent.com/wh1te909/tacticalrmm/master/update.sh
tactical@tacrmm:~$ chmod +x update.sh
tactical@tacrmm:~$ ./update.sh
```

<br/>

If you are already on the latest version, the update script will notify you of this and return immediately.<br/><br/>
You can pass the optional `--force` flag to the update script to forcefully run through an update, which will bypass the check for latest version.<br/>
```bash
tactical@tacrmm:~$ ./update.sh --force
```
This is usefull for a botched update that might have not completed fully.<br/><br/>
The update script will also fix any permissions that might have gotten messed up during a botched update, or if you accidentally ran the update script as the `root` user.