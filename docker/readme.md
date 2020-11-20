# Docker Setup

- Install docker and docker-compose
- Optional (but strongly recommended) obtain valid wildcard certificate for domain. If certificates are not provided, a self-signed cert will be generated. See below on how to generate a free Let's Encrypt!

## (Optional) Generate certificates with certbot
Install Certbot

```
sudo add-apt-repository ppa:certbot/certbot
sudo apt-get install certbot
```

Generate the wildcard certificate. Add the DNS entry for domain validation. Replace `example.com` with your root doamin

```
sudo certbot certonly --manual -d *.example.com --agree-tos --no-bootstrap --manual-public-ip-logging-ok --preferred-challenges dns
```

## Configure DNS and Firewall

You will need to add DNS entries so that the three subdomains resolve to the IP of the docker host. There is a reverse proxy running that will route the hostnames to the correct container. On the host, you will need to ensure the firewall is open on tcp ports 80, 443, 4505, 4506.

## Run the environment with Docker

Get the docker-compose and .env.example file on the host you which to install on

```
wget https://raw.githubusercontent.com/wh1te909/tacticalrmm/master/docker/docker-compose.yml
wget https://raw.githubusercontent.com/wh1te909/tacticalrmm/master/docker/.env.example
mv .env.example .env
```

Change the values in .env to match your environment.

If you are supplying certificates through Let's Encrypt or another source, see the section below about base64 encoding the certificate files. 

Then run the below command to start the environment.

```
sudo docker-compose up -d
```

## Get MeshCentral EXE download link

Run the below command to get the download link for the mesh central exe. This needs to be uploaded on first successful signin.

```
sudo docker-compose exec tactical-backend python manage.py get_mesh_exe_url
```

## Base64 encoding certificates to pass as env variables

Use the below command to add the the correct values to the .env.

Running this command multiple times will add redundant entries, so those will need to be removed.

Let's encrypt certs are stored in:

public key
`/etc/letsencrypt/live/${rootdomain}/fullchain.pem`

private key
`/etc/letsencrypt/live${rootdomain}/privkey.pem`

```
sudo echo "CERT_PUB_KEY=$(base64 /path/to/pub/key)" >> .env
sudo echo "CERT_PRIV_KEY=$(base64 /path/to/priv/key)" >> .env
```
