# Viewsfer - Remote Access Software

Remote monitoring & management tool for Windows computers

## Features

- Remote desktop control
- Remote shell
- Remote file manager (download and upload files)
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
login as root and create vsf user
```
apt update && apt -y upgrade
adduser vsf
usermod -a -G sudo vsf
```

switch to the vsf user and setup the firewall
```
su - vsf
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw allow proto tcp from any to any port 4505,4506
sudo ufw enable && sudo ufw reload
```

Our domain for this example is viewsfer.com

In the DNS manager of wherever our domain is hosted, we will create three A records, all pointing to the public IP address of our VPS

Create A record ```api.tacticalrmm.com``` for the django rest backend\
Create A record ```rmm.tacticalrmm.com``` for the vue frontend\
Create A record ```mesh.tacticalrmm.com``` for meshcentral

Download the install script and run it

```
wget https://raw.githubusercontent.com/softicious/viewsfer/develop/install.sh
chmod +x install.sh
./install.sh
```
```
