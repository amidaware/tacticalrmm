# Tactical RMM

[![Build Status](https://travis-ci.com/wh1te909/tacticalrmm.svg?branch=develop)](https://travis-ci.com/wh1te909/tacticalrmm)
[![Build Status](https://dev.azure.com/dcparsi/Tactical%20RMM/_apis/build/status/wh1te909.tacticalrmm?branchName=develop)](https://dev.azure.com/dcparsi/Tactical%20RMM/_build/latest?definitionId=4&branchName=develop)
[![Coverage Status](https://coveralls.io/repos/github/wh1te909/tacticalrmm/badge.png?branch=develop&kill_cache=1)](https://coveralls.io/github/wh1te909/tacticalrmm?branch=develop)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)

Tactical RMM is a remote monitoring & management tool for Windows computers, built with Django and Vue.\
It uses an [agent](https://github.com/wh1te909/rmmagent) written in golang, as well as the [SaltStack](https://github.com/saltstack/salt) api and [MeshCentral](https://github.com/Ylianst/MeshCentral)

# [LIVE DEMO](https://rmm.xlawgaming.com/)
Demo database resets every hour. Alot of features are disabled for obvious reasons due to the nature of this app.

*Tactical RMM is currently in alpha and subject to breaking changes. Use in production at your own risk.*

### [Discord Chat](https://discord.gg/upGTkWp)

## Features

- Teamviewer-like remote desktop control
- Real-time remote shell
- Remote file browser (download and upload files)
- Remote command and script execution (batch, powershell and python scripts)
- Event log viewer
- Services management
- Windows patch management
- Automated checks with email/SMS alerting (cpu, disk, memory, services, scripts, event logs)
- Automated task runner (run scripts on a schedule)
- Remote software installation via chocolatey
- Software and hardware inventory

## Windows versions supported

- Windows 7, 8.1, 10, Server 2008R2, 2012R2, 2016, 2019

## Installation

### Requirements
- VPS with 4GB ram (an install script is provided for Ubuntu Server 20.04)
- A domain you own with at least 3 subdomains
- Google Authenticator app (2 factor is NOT optional)

### Docker
Refer to the [docker setup](docker/readme.md)


### Installation example (Ubuntu server 20.04 LTS)

Fresh VPS with latest updates\
login as root and create a user and add to sudoers group (we will be creating a user called tactical)
```
apt update && apt -y upgrade
adduser tactical
usermod -a -G sudo tactical
```

switch to the tactical user and setup the firewall
```
su - tactical
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw allow proto tcp from any to any port 4505,4506
sudo ufw enable && sudo ufw reload
```

Our domain for this example is tacticalrmm.com

In the DNS manager of wherever our domain is hosted, we will create three A records, all pointing to the public IP address of our VPS

Create A record ```api.tacticalrmm.com``` for the django rest backend\
Create A record ```rmm.tacticalrmm.com``` for the vue frontend\
Create A record ```mesh.tacticalrmm.com``` for meshcentral

Download the install script and run it

```
wget https://raw.githubusercontent.com/wh1te909/tacticalrmm/develop/install.sh
chmod +x install.sh
./install.sh
```

 Links will be provided at the end of the install script.\
 Download the executable from the first link, then open ```rmm.tacticalrmm.com``` and login.\
 Upload the executable when prompted during the initial setup page.


### Install an agent
From the app's dashboard, choose Agents > Install Agent to generate an installer.

## Updating
Download and run [update.sh](./update.sh) ([Raw](https://raw.githubusercontent.com/wh1te909/tacticalrmm/develop/update.sh))
```
wget https://raw.githubusercontent.com/wh1te909/tacticalrmm/develop/update.sh
chmod +x update.sh
./update.sh
```

## Backup
Download [backup.sh](./backup.sh) ([Raw](https://raw.githubusercontent.com/wh1te909/tacticalrmm/develop/backup.sh))
```
wget https://raw.githubusercontent.com/wh1te909/tacticalrmm/develop/backup.sh
```
Change the postgres username and password at the top of the file (you can find them in `/rmm/api/tacticalrmm/tacticalrmm/local_settings.py` under the DATABASES section)

Run it
```
chmod +x backup.sh
./backup.sh
```

## Restore
Change your 3 A records to point to new server's public IP

Create same linux user account as old server and add to sudoers group and setup firewall (see install instructions above)

Copy backup file to new server

Download the restore script, and edit the postgres username/password at the top of the file. Same instructions as above in the backup steps.
```
wget https://raw.githubusercontent.com/wh1te909/tacticalrmm/develop/restore.sh
```

Run the restore script, passing it the backup tar file as the first argument
```
chmod +x restore.sh
./restore.sh rmm-backup-xxxxxxx.tar
```

## Using another ssl certificate
During the install you can opt out of using the Let's Encrypt certificate. If you do this the script will create a self-signed certificate, so that https continues to work. You can replace the certificates in /certs/example.com/(privkey.pem | pubkey.pem) with your own. 

If you are migrating from Let's Encrypt to another certificate provider, you can create the /certs directory and copy your certificates there. It is recommended to do this because this directory will be backed up with the backup script provided. Then modify the nginx configurations to use your new certificates

The cert that is generated is a wildcard certificate and is used in the nginx configurations: rmm.conf, api.conf, and mesh.conf. If you can't generate wildcard certificates you can create a cert for each subdomain and configure each nginx configuration file to use its own certificate. Then restart nginx:

```
sudo systemctl restart nginx
```