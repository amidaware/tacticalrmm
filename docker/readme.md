# Docker Setup

- install docker and docker-compose
- Obtain wildcard cert or individual certs for each subdomain
- You can copy any wildcard cert public and private key to the docker/nginx-proxy/certs folder.

## Generate certificates with certbot (Optional if you already have the certs)

Install Certbot

```
sudo add-apt-repository ppa:certbot/certbot
sudo apt-get install certbot
```

Generate the wildcard certificate. Add the DNS entry for domain validation.

```
sudo certbot certonly --manual -d *.example.com --agree-tos --no-bootstrap --manual-public-ip-logging-ok --preferred-challenges dns
```
Copy the fullchain.pem and privkey.pem to the nginx-proxy/cert directory.

## Configure DNS and Firewall

You will need to add DNS entries so that the three subdomains resolve to the IP of the docker host. There is a reverse proxy running that will route the hostnames to the correct container. On the host, you will need to ensure the firewall is open on tcp ports 80, 443, 4505, 4506.

## Run the environment with Docker

Copy the .env.example to .env then
change values in .env to match your environment

```
cd docker
sudo docker-compose up -d
```

You may need to run this twice if some containers fail to start

## Create a super user

```
sudo docker-compose exec api python manage.py createsuperuser
```

## Get MeshCentral EXE download link

Run the below command to get the download link for the mesh central exe. The dashboard will ask for this when you first sign in

```
sudo docker-compose exec api python manage.py get_mesh_exe_url
```

## Connect to a container instance shell

The below command opens up a shell to the api service.

```
sudo docker-compose exec api /bin/bash
```

If /bin/bash doesn't work then /bin/sh might need to be used.

## Using Docker for Dev (optional)

This allows you to edit the files locally and those changes will be presented to the containers. Hot Module Reload (Vue/webpack) and the Python equivalent will also work!

### Setup

Files that need to be manually created are:
- api/tacticalrmm/tacticalrmm/local_settings.py
- web/.env

Make sure to add `MESH_WS_URL="ws://meshcentral:443"` in the local_settings.py file. This is needed for the mesh central setup

For HMR to work with vue you can copy .env.example and modify the setting to fit your dev environment.

### Create Python Virtual Env

Each python container shares the same virtual env to make spinning up faster. It is located in api/tacticalrmm/env.

There is a container dedicated to creating and keeping this up to date. Prior to spinning up the environment you can run `docker-compose -f docker-compose.yml -f docker-compose.dev.yml up venv` to make sure the virtual env is ready. Otherwise the api and celery containers will fail to start.

### Spinup the environment

Now run `docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d` to spin everything else up

This will mount the local vue and python files in the app container with hot reload. Does not require rebuilding when changes to code are made and the changes will take effect immediately!

### Other Considerations

- It is recommended that you use the vscode docker plugin to manage containers. Docker desktop works well too on Windows.
