# Updating the RMM

## Keeping your linux server up to date

You should periodically run `sudo apt update` and `sudo apt -y upgrade` to keep your server up to date.

Other than this, you should avoid making any changes to your server and let the `update.sh` script handle everything else for you.

## Updating to the latest RMM version

!!!danger
    Do __not__ attempt to manually edit the update script or any configuration files unless specifically told to by one of the developers.
    
    Since this software is completely self hosted and we have no access to your server, we have to assume you have not made any config changes to any of the files or services on your server, and the update script will assume this.
    
    You should also **never** attempt to automate running the update script via cron.
    
    The update script will update itself if needed to the latest version when you run it, and then prompt you to run it again.
    
    Sometimes, manual intervention will be required during an update in the form of yes/no prompts, so attempting to automate this will ignore these prompts and cause your installation to break.

SSH into your server as the linux user you created during install (eg `tactical`).

!!!danger
    __Never__ run any update scripts or commands as the `root` user.
    
    This will mess up permissions and break your installation.

!!!question
    You have a [backup](backup.md) right?

Download the update script and run it:

```bash
wget -N https://raw.githubusercontent.com/wh1te909/tacticalrmm/master/update.sh
chmod +x update.sh
./update.sh
```

If you are already on the latest version, the update script will notify you of this and return immediately.

You can pass the optional `--force` flag to the update script to forcefully run through an update, which will bypass the check for latest version.

```bash
./update.sh --force
```

This is useful for a botched update that might have not completed fully.

The update script will also fix any permissions that might have gotten messed up during a botched update, or if you accidentally ran the update script as the `root` user.

!!!warning
    Do __not__ attempt to manually update MeshCentral to a newer version.

    You should let the `update.sh` script handle this for you. 
    
    The developers will test MeshCentral and make sure integration does not break before bumping the mesh version.

## Keeping your Let's Encrypt certificate up to date

!!!info
    Currently, the update script does not automatically renew your Let's Encrypt wildcard certificate, which expires every 3 months, since this is non-trivial to automate using the DNS TXT record method.

To renew your Let's Encrypt wildcard cert, run the following command, replacing `example.com` with your domain and `admin@example.com` with your email:

```bash
sudo certbot certonly --manual -d *.example.com --agree-tos --no-bootstrap --manual-public-ip-logging-ok --preferred-challenges dns -m admin@example.com --no-eff-email
```

Same instructions as during install for [verifying the TXT record](install_server.md#deploy-the-txt-record-in-your-dns-manager) has propagated before hitting ++enter++.

After this you have renewed the cert, simply run the `update.sh` script, passing it the `--force` flag.

```bash
./update.sh --force
```

## Keep an eye on your disk space

If you're running low, shrink you database

1. Choose *Tools menu > Server Maintenance > Prune DB Tables*

2. At server command prompt run

```bash
sudo -u postgres psql -d tacticalrmm -c "vacuum full logs_auditlog"
sudo -u postgres psql -d tacticalrmm -c "vacuum full logs_pendingaction"
```

## Video Walkthru

<div class="video-wrapper">
  <iframe width="320" height="180" src="https://www.youtube.com/embed/ElUfQgesYs0" frameborder="0" allowfullscreen></iframe>
</div>
