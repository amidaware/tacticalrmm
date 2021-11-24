# Restore

!!!info
    It is currently not possible to restore to a different domain/subdomain, only to a different physical or virtual server.

!!!danger
    The restore script will always restore to the latest available RMM version on github.

    Make sure you update your old RMM to the latest version using the `update.sh` script and then run a fresh backup to use with this restore script.

## Install the new server

### Run Updates on OS

SSH into the server as **root**.

Download and run the prereqs and latest updates

```bash
apt update
apt install -y wget curl sudo
apt -y upgrade
```

If a new kernel is installed, then reboot the server with the `reboot` command

### Create a linux user

Create a linux user named `tactical` to run the rmm and add it to the sudoers group.

**For Ubuntu**:

```bash
adduser tactical
usermod -a -G sudo tactical
```

**For Debian**:

```bash
useradd -m -s /bin/bash tactical
usermod -a -G sudo tactical
```

!!!tip
    [Enable passwordless sudo to make your life easier in the future](https://linuxconfig.org/configure-sudo-without-password-on-ubuntu-20-04-focal-fossa-linux)

### Setup the firewall (optional but highly recommended)

!!!info
    Skip this step if your VM is __not__ publicly exposed to the world e.g. running behind NAT. You should setup the firewall rules in your router instead (ports 22, 443 and 4222 TCP).

```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow https
ufw allow proto tcp from any to any port 4222
```

!!!info
    SSH (port 22 tcp) is only required for you to remotely login and do basic linux server administration for your rmm. It is not needed for any agent communication.<br/>
Allow ssh from everywhere (__not__ recommended)

```bash
ufw allow ssh
```

Allow ssh from only allowed IP's (__highly__ recommended)

```bash
ufw allow proto tcp from X.X.X.X to any port 22
ufw allow proto tcp from X.X.X.X to any port 22
```

Enable and activate the firewall

```bash
ufw enable && ufw reload
```

!!!note
    You will never login to the server again as `root` again unless something has gone horribly wrong, and you're working with the developers.
    

## Change DNS A records

Open the DNS manager of wherever your domain is hosted.

Change the 3 A records `rmm`, `api` and `mesh` and point them to the public IP of your new server.

## Run the restore script

1. Make sure you're logged in with the non-root user (eg `tactical`)

2. Copy the backup tar file you created during [backup](backup.md) to the new server.

3. Download the restore script.

        wget https://raw.githubusercontent.com/wh1te909/tacticalrmm/master/restore.sh
        chmod +x restore.sh

4. Call the restore script, passing it the backup file as the first argument:

```bash
./restore.sh rmm-backup-XXXXXXXXX.tar
```
