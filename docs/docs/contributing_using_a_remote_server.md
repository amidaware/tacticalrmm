# Contributing Using a Remote Server

The below instructions are for a non-production server that has Tactical RMM installed and configured with a real domain. You can then use your own GitHub to push changes to and then submit a PR request to the TRMM `develop` branch (<https://github.com/wh1te909/tacticalrmm>).

!!!warning
    Do not attempt development of this kind on your production server.

## Install Tacticall RMM

### 1. Traditional install

This guide assumes you have done a [Traditional Install](install_server.md).

### 2. Install VSCode and Extensions
Download VSCode [here](https://code.visualstudio.com/download)

Download the Remote SSH Development Pack [here](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.vscode-remote-extensionpack)

## Configure the Remote Development Server
### 1. Connect

The remote development server should already have Tactical RMM installed via the traditional install method.

After the extension pack is installed in VSCode you will have a new button at the bottom-left of VSCode. You can select it and add your remote SSH host information.

![RemoteSSH](images/Remote_SSH_connection.png)

### 2. Configure

Configuring a remote server for development work is necessary so that as you make changes to the code base it will automatically refresh and you can see the changes. It may be necessary to do a full browser refresh if changing styles.

Disable RMM and Daphne services

```bash
sudo systemctl disable --now rmm.service && sudo systemctl disable --now daphne.service
```

Open /rmm/web/.env and make it look like the following

```bash
DEV_URL = "http://api.EXAMPLE.COM:8000"
APP_URL = "http://rmm.EXAMPLE.COM:8080"
```

Open /rmm/api/tacticalrmm/tacticalrmm/local_settings.py

```bash
change DEBUG = True
```
Remove
```bash
CORS_ORIGIN_WHITELIST list
```
Add
```bash
CORS_ORIGIN_ALLOW_ALL = True
```

Add the following to the ALLOWED HOSTS
```bash
rmm.EXAMPLE.COM
```
cd /rmm/api/tacticalrmm/

```bash
source ../env/bin/activate
```

Install requirements

```bash
pip install -r requirements-dev.txt -r requirements-test.txt
```

Start Django backend

```bash
python manage.py runserver 0:8000
```

Open a new terminal and compile quasar frontend

```bash
cd /rmm/web
npm install
npm install -g @quasar/cli
quasar dev
```

!!!info If you receive a CORS error when trying to log into your server via localhost or IP, try the following
```bash
rm -rf node_modules .quasar
npm install
quasar dev
```
You should now have a localhost and IP based URL to view that has a live reload feature.

## Configure GitHub with VSCode
!!!info Make sure you are submitting Pull Requests to the develop branch.
Follow this guide for a good introduction to GitHub: <https://www.digitalocean.com/community/tutorials/how-to-create-a-pull-request-on-github>

Make sure u are on develop branch
```bash
git checkout develop
```
git remote -v should look like the following
```bash
origin  https://github.com/yourusername/tacticalrmm.git (fetch)
origin  https://github.com/yourusername/tacticalrmm.git (push)
upstream https://github.com/wh1te909/tacticalrmm.git (fetch)
upstream https://github.com/wh1te909/tacticalrmm.git (push)
```
You will commit the change to your GitHub and from within GitHub you can then submit a PR to the develop branch of wh1te909 Tactical RMM.

More to come...