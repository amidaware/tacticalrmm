# Updating the RMM

#### Keeping your linux server up to date

You should periodically run `sudo apt update` and `sudo apt -y upgrade` to keep your server up to date.

Other than this, you should avoid making any changes to your server and let the `update.sh` script handle everything else for you.
#### Updating to the latest RMM version

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
wget -N https://raw.githubusercontent.com/wh1te909/tacticalrmm/master/update.sh
chmod +x update.sh
./update.sh
```

<br/>

If you are already on the latest version, the update script will notify you of this and return immediately.<br/><br/>
You can pass the optional `--force` flag to the update script to forcefully run through an update, which will bypass the check for latest version.<br/>
```bash
./update.sh --force
```
This is usefull for a botched update that might have not completed fully.<br/><br/>
The update script will also fix any permissions that might have gotten messed up during a botched update, or if you accidentally ran the update script as the `root` user.

<br/>


!!!warning
    Do __not__ attempt to manually update MeshCentral to a newer version.
    
    You should let the `update.sh` script handle this for you. 
    
    The developers will test MeshCentral and make sure integration does not break before bumping the mesh version.

#### Keeping your Let's Encrypt certificate up to date

!!!info
    Currently, the update script does not automatically renew your Let's Encrypt wildcard certificate, which expires every 3 months, since this is non-trivial to automate using the DNS TXT record method.

To renew your Let's Encrypt wildcard cert, run the following command, replacing `example.com` with your domain and `admin@example.com` with your email:

```bash
sudo certbot certonly --manual -d *.example.com --agree-tos --no-bootstrap --manual-public-ip-logging-ok --preferred-challenges dns -m admin@example.com --no-eff-email
```

Same instructions as during install for [verifying the TXT record](install_server.md#deploy-the-txt-record-in-your-dns-manager) has propogated before hitting Enter.

After this you have renewed the cert, simply run the `update.sh` script, passing it the `--force` flag.

```bash
./update.sh --force
```
