# Docker Setup

- Install docker and docker-compose
- Obtain valid wildcard certificate for your domain. If certificates are not provided, a self-signed certificate will be generated and most agent functions won't work. See below on how to generate a free Let's Encrypt!

## Generate certificates with certbot

Install Certbot

```bash
sudo apt-get install certbot
```

Generate the wildcard certificate. Add the DNS entry for domain validation. Replace `example.com` with your root doamin

```bash
sudo certbot certonly --manual -d *.example.com --agree-tos --no-bootstrap --manual-public-ip-logging-ok --preferred-challenges dns
```

## Configure DNS and firewall

You will need to add DNS entries so that the three subdomains resolve to the IP of the docker host. There is a reverse proxy running that will route the hostnames to the correct container. On the host, you will need to ensure the firewall is open on tcp ports 80, 443 and 4222.

## Setting up the environment

Get the docker-compose and .env.example file on the host you which to install on

```bash
wget https://raw.githubusercontent.com/wh1te909/tacticalrmm/master/docker/docker-compose.yml
wget https://raw.githubusercontent.com/wh1te909/tacticalrmm/master/docker/.env.example
mv .env.example .env
```

Change the values in .env to match your environment.

If you are supplying certificates through Let's Encrypt or another source, see the section below about base64 encoding the certificate files.

## Base64 encoding certificates to pass as env variables

Use the below command to add the the correct values to the .env.

Running this command multiple times will add redundant entries, so those will need to be removed.

Let's encrypt certs paths are below. Replace ${rootdomain} with your own.

public key
`/etc/letsencrypt/live/${rootdomain}/fullchain.pem`

private key
`/etc/letsencrypt/live/${rootdomain}/privkey.pem`

```bash
echo "CERT_PUB_KEY=$(sudo base64 -w 0 /path/to/pub/key)" >> .env
echo "CERT_PRIV_KEY=$(sudo base64 -w 0 /path/to/priv/key)" >> .env
```

## Starting the environment

Run the below command to start the environment.

```bash
sudo docker-compose up -d
```

Removing the -d will start the containers in the foreground and is useful for debugging.

## Get MeshCentral EXE download link

Run the below command to get the download link for the mesh central exe. This needs to be uploaded on first successful signin.

```bash
sudo docker-compose exec tactical-backend python manage.py get_mesh_exe_url
```

## Backups

The backup script **does not** work with docker. To backup your install use [standard docker backup/restore](https://docs.docker.com/desktop/backup-and-restore/) processes.
