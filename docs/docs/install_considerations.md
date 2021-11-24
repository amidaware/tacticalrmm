# Install Considerations

There's pluses and minuses to each install type. Be aware that:

- There is no migration script, once you've installed with one type there is no "conversion". You'll be installing a new server and migrating agents manually if you decide to go another way.

## Traditional Install

- It's a VM/machine. One storage device to backup if you want to do VM based backups
- You have a [backup](backup.md) and [restore](restore.md) script

## Docker Install

- Docker is more complicated in concept: has volumes and images
- If you're running multiple apps it uses less resources in the long run because you only have one OS base files underlying many Containers/Apps
- Backup/restore is via Docker methods only
- Docker has container replication/mirroring options for redundancy/multiple servers
