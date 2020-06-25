# Tactical RMM

[![Build Status](https://travis-ci.com/wh1te909/tacticalrmm.svg?branch=develop)](https://travis-ci.com/wh1te909/tacticalrmm)
[![Build Status](https://dev.azure.com/dcparsi/Tactical%20RMM/_apis/build/status/wh1te909.tacticalrmm?branchName=develop)](https://dev.azure.com/dcparsi/Tactical%20RMM/_build/latest?definitionId=4&branchName=develop)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)

Tactical RMM is a remote monitoring & management tool for Windows computers, built with Django and Vue.\
It uses an [agent](https://github.com/wh1te909/winagent) written in python, as well as the [SaltStack](https://github.com/saltstack/salt) api and [MeshCentral](https://github.com/Ylianst/MeshCentral)

*Tactical RMM is currently in alpha and subject to breaking changes. Use in production at your own risk.*

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
- VPS with 2GB ram (an install script is provided for Ubuntu Server 20.04)
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

Download and run [update.sh](./update.sh)