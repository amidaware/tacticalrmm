# Docker Setup

- install docker and docker-compose
- Obtain wildcard cert or individual certs for each subdomain

## Generate certificates with certbot

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

You will need to add DNS entries so that the three subdomains resolve to the IP of the docker host. There is a reverse proxy running that will route the hostnames to the correct container. On the host, you will need to ensure the firewall is open on tcp ports 80, 443, 8123, 4505, 4506.

## Run the environment with Docker

Copy the .env.example to .env then
change values in .env to match your environment

```
cd docker
sudo docker-compose up -d
```

You may need to run this twice since some of the dependant containers won't be ready

## Create a super user

```
sudo docker-compose exec api python manage.py createsuperuser
```

## Setup 2FA authentication

Get the 2FA code with 

```
sudo docker-compose exec api python manage.py generate_totp
```

Add the generated code to the .env file TWO_FACTOR_OTP in the docker folder

## Generate the meshcentral login token key

Get the login token key with

```
sudo docker-compose exec meshcentral node node_modules/meshcentral/meshcentral --logintokenkey
```

Add the generated key to the .env file MESH_TOKEN_KEY in the docker folder

Rebuild the api container

```
sudo docker-compose up -d --build api
```

Use the generated code and the username to generate a bar code for your authenticator app

```
sudo docker-compose exec api python manage.py generate_barcode [OTP_CODE] [username]
```

## Connect to a container instance shell

The below command opens up a shell to the api service.

```
sudo docker-compose exec api /bin/bash
```

If /bin/bash doesn't work then /bin/sh might need to be used.

## Using Docker for Dev

run `docker-compose -f docker-compose.yml -f docker-compose.dev.yml up`

This will mount the local vue files in the app container with hot reload.