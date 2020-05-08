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


Use the generated code and the username to generate a bar code for your authenticator app
(domain is the domain name of your site, for example: rmm.example.com)

```
sudo docker-compose exec api python manage.py generate_barcode [2FAcode] [username] [domain]
```



## Generate the meshcentral login token key

Get the login token key with

```
sudo docker-compose exec meshcentral node node_modules/meshcentral/meshcentral --logintokenkey
```

Add the generated key to the .env file MESH_TOKEN_KEY in the docker folder

## Rebuild the api container

```
sudo docker-compose up -d --build api
```

## Connect to a container instance shell

The below command opens up a shell to the api service.

```
sudo docker-compose exec api /bin/bash
```

If /bin/bash doesn't work then /bin/sh might need to be used.

## Using Docker for Dev

This allows you to edit the files locally and those changes will be presented to the conatiners. Hot Module Reload (Vue/webpack) and the Python equivalent will also work!

### Setup

Files that need to be manually created are:
- api/tacticalrmm/tacticalrmm/local_settings.py
- web/.env.local

For HMR to work with vue you may need to alter the web/vue.config.js file to with these changes

```
  devServer: {
    //host: "192.168.99.150",
    disableHostCheck: true,
    public: "YOUR_APP_URL"
  },
```

Since this file is checked into git you can configure git to ignore it and the changes will stay intact

```
git update-index --assume-unchanged ./web/vue.config.js
```

To revert this run

```
git update-index --no-assume-unchanged ./web/vue.config.js
```

### Create Python Virtual Env

Each python container shares the same virtual env to make spinning up faster. It is located in api/tacticalrmm/env.

There is a container dedicated to creating and keeping this up to date. Prior to spinning up the environment you can run `docker-compose -f docker-compose.dev.yml up venv` to make sure the virtual env is ready. Otherwise the api and celery containers will fail to start.

### Spinup the environment

Now run `docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d` to spin everything else up

This will mount the local vue and python files in the app container with hot reload. Does not require rebuilding when changes to code are made and the changes will take effect immediately!

### Running the Tests

There is a container that is dedicated to run the vue unit tests. The below command will run them and display the output. You can ignore the orphaned containers message.

```
docker-compose -f docker-compose.test.yml up app-unit-test
```

### Other Considerations

- Using Docker Desktop on Windows will provide more visibility into which containers are running. You also can easily view the logs for each container in real-time, and view container environment variables.

- If you are on a *nix system, you can get equivalent logging by using `docker-compose logs [service_name]`.

- `docker ps` will show running containers.

- `docker system prune` will remove items that are not in use by running containers. There are also `--all and --volumes` options to remove everything if you want to start over. Stop running containers first. `docker-compose -f docker-compose.yml -f docker-compose.dev.yml down`

- If the docker container isn't getting file changes you can restart the host or do a `docker system prune --volumes`. This will remove the docker volumes and will create a new one once the containers are started.
