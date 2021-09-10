# Contributing Using a Remote Server

The below instructions are for a development server that has Tactical RMM installed and configured with a real domain. You can then use your own GitHub to push changes to and then submit a PR request to the TRMM `develop` branch (<https://github.com/wh1te909/tacticalrmm>).

!!!warning
    Please do not attempt development of this kind on your production server.

## Getting Started

### 1. Install Tactical RMM per instructions

Do a [Traditional Install](https://wh1te909.github.io/tacticalrmm/install_server/)

### 2. Install VSCode

<https://code.visualstudio.com/download>

#### 2a. Install VSCode Remote SSH Development Pack

<https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.vscode-remote-extensionpack>

### 3. Connect to your remote development server

After the extension pack is installed you will have a new button at the bottom-left of VSCode. You can select it and add your remote SSH host information.

![RemoteSSH](images/Remote_SSH_connection.PNG)

### 4. Configure remote server

Configuring a remote server for development work is necessary so that as you make changes to the code base you can refresh your browse anr and thest htem them out before pushing to your GitHBUub fork to then submit a PR.

- Disable rmm and daphne services

```bash
sudo systemctl disable --now rmm.service && sudo systemctl disable --now daphne.service
```

- Open /rmm/web/.env and make it look like the following

```bash
DEV_URL = "http://api.domain.com:8000"
APP_URL = "http://rmm.domain.com:8080"
```

- Open /rmm/api/tacticalrmm/tacticalrmm/local_settings.py

```bash
remove CORS_ORIGIN_WHITELIST list
add CORS_ORIGIN_ALLOW_ALL = True
```

```bash
change DEBUG = True
```

- cd /rmm/api/tacticalrmm/

```bash
source ../env/bin/activate
```

- Install requirements

```bash
pip install -r requirements-dev.txt -r requirements-test.txt
```

- Start Django backend

```bash
python manage.py runserver 0:8000
```

- Compile quasar frontend

```bash
cd /rmm/web
npm install
quasar dev
```

- If you get quasar command not found

```bash
npm install -g @quasar/cli
```

- If you receive a CORS error when trying to log into your server via localhost or IP

```bash
rm -rf node_modules .quasar
npm install
quasar dev
```

- Make sure u are on develop branch

```bash
git checkout develop
```

### 5. Fork Project in Github

This is making a duplicate of the code under your Github that you can edit

<https://github.com/wh1te909/tacticalrmm>

![ForkIt](images/vscode-forkit.png)

### 6. Add your (forked) repo to vscode

Clone repository

Login to your Github

Remote - SSH

### 7. Configure a remote for your fork (in vscode)

<https://docs.github.com/en/github/collaborating-with-issues-and-pull-requests/configuring-a-remote-for-a-fork>

Configure your local fork and tell it where the original code repo is so you can compare and merge updates later when official repo is updated

Add upstream repo

```bash
git remote add upstream https://github.com/your username/tacticalrmm
```

git remove -v should look like the following

```bash
tacticalrmm     https://github.com/yourusername/tacticalrmm (fetch)
tacticalrmm     https://github.com/yourusername/tacticalrmm (push)es
```
