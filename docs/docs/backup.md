# Backing up the RMM

!!!note
        This is only applicable for the standard install, not Docker installs.

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

# Schedule to run daily via cron

Make a symlink in `/etc/cron.d` (daily cron jobs) with these contents `00 18 * * * tactical /rmm/backup.sh` to run at 6pm daily.

```bash
echo -e "\n" >> /rmm/backup.sh
sudo ln -s /rmm/backup.sh /etc/cron.daily/
```

# Video Walkthru

<div class="video-wrapper">
  <iframe width="320" height="180" src="https://www.youtube.com/embed/rC0NgYJUf_8" frameborder="0" allowfullscreen></iframe>
</div>
