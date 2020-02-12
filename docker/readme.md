# Docker Setup

- install docker and docker-compose
- Obtain wildcard cert or individual certs for each subdomain

## Optional - Generate certificates with certbot

Install Certbot

```sudo add-apt-repository ppa:certbot/certbot
sudo apt-get install certbot
```

Generate the wildcard certificate. Add the DNS entry for domain validation.

```sudo certbot certonly --manual -d *.example.com --agree-tos --no-bootstrap --manual-public-ip-logging-ok --preferred-challenges dns
```
Copy the fullchain.pem and privkey.pem to the cert directory.

## Run the environment with Docker

Change values in .env to match your environment

```cd docker
sudo docker-compose up -d
```

You may need to run this twice since some of the dependant containers won't be ready

## Create a super user

```sudo docker exec -it docker_api_1 python manage.py createsuperuser
```

## Setup 2FA authentication

Get the 2FA code with 

```sudo docker exec -it docker_api_1 python manage.py generate_totp
```

Add the generated code to the .env file TWO_FACTOR_OTP in the docker folder

Rebuild the api container

```sudo docker-compose up -d --build api
```

Use the generated code and the username to generate a bar code for your authenticator app

```sudo docker exec -it docker_api_1 python manage.py generate_barcode [OTP_CODE] [username]
```
