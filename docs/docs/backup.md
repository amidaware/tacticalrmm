# Backing up the RMM

A backup script is provided for quick and easy way to backup all settings into one file to move to another server.

Download the backup script:
```bash
wget -N https://raw.githubusercontent.com/wh1te909/tacticalrmm/master/backup.sh
```

From the Web UI, click **Tools > Server Maintenance**

Choose **Prune DB Tables** from the dropdown and check the `Audit Log` and `Pending Actions` checkboxes, and then click **Submit**

Doing a prune first before running the backup will significantly speed up the postgres vacuum command that is run during backup.

Run the backup script

```bash
chmod +x backup.sh
./backup.sh
```

The backup tar file will be saved in `/rmmbackups` with the following format:

`rmm-backup-CURRENTDATETIME.tar`

