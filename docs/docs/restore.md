# Restore

!!!info
    It is currently not possible to restore to a different domain/subdomain, only to a different physical or virtual server.

!!!danger
    You must update your old RMM to the latest version using the `update.sh` script before attempting to restore.
#### Prepare the new server
Create the same exact linux user account as you did when you installed the original server.

Add it to the sudoers group and setup the firewall.

Refer to the [installation instructions](install_server.md) for steps on how to do all of the above.

#### Change DNS A records
Open the DNS manager of wherever your domain is hosted.

Change the 3 A records `rmm`, `api` and `mesh` and point them to the public IP of your new server.

#### Run the restore script

Copy the backup tar file you created during [backup](backup.md) to the new server.

Download the restore script.

```bash
wget https://raw.githubusercontent.com/wh1te909/tacticalrmm/master/restore.sh
```

Call the restore script, passing it the backup file as the first argument:

```bash
sudo chmod +x restore.sh
./restore.sh rmm-backup-XXXXXXXXX.tar
```
