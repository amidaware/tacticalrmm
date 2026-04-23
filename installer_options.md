# Installer Options for latest revision  
### Static IP for Tactical RMM: 123.456.789.012  
### Tactical User: tactical  
### Tactical Password: SuperVerySecurePasswordHere  

### Recommended disk mounts under Ubuntu for Simplified Reinstallation if required.  
### /var/lib/postgresql → 200GB (Optional)  
### /rmmbackups         → 300GB (Optional)  
### /meshcentral        → 100GB (Optional)  
### /var/log            → 15GB  (Optional)  

```
# Install Process once setup
sudo apt update
sudo apt -y dist-upgrade
sudo apt install -y wget curl sudo ufw

sudo useradd -m -G sudo -s /bin/bash tactical
sudo passwd tactical

# Tactical Password required at this point.

sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow https
sudo ufw allow ssh

sudo ufw enable && ufw reload

su - tactical

# Tactical Password required at this point.
```
## ##Recommended to Snapshot/Backup System at this point for easy recovery##

```
nano install.sh (I was manually updating the installer)
chmod +x install.sh

# Tactical Password required at this point.

export djangopassword='adminportalpassword'
Cloudflare_token='cloudflaretoken' \
rmmdomain='api.example.com' \
frontenddomain='rmm.example.com' \
meshdomain='mesh.example.com' \
rootdomain='example.com' \
letsemail='username@example.com' \
djangousername='sysadmin' \
./install.sh
```