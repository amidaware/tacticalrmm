# Updating the RMM (Docker)

#### Updating to the latest RMM version

Tactical RMM updates the docker images on every release and should be available within a few minutes

SSH into your server as a root user and run the below commands:<br/>
```bash
cd [dir/with/compose/file]
mv docker-compose.yml docker-compose.yml.old
wget https://raw.githubusercontent.com/wh1te909/tacticalrmm/master/docker/docker-compose.yml
sudo docker-compose pull
sudo docker-compose down
sudo docker-compose up -d --remove-orphans
```

#### Keeping your Let's Encrypt certificate up to date

To renew your Let's Encrypt wildcard cert, run the following command, replacing `example.com` with your domain and `admin@example.com` with your email:

```bash
sudo certbot certonly --manual -d *.example.com --agree-tos --no-bootstrap --manual-public-ip-logging-ok --preferred-challenges dns -m admin@example.com --no-eff-email
```

Verify the domain with the TXT record. Once issued, run the below commands to base64 encode the certificates and add then to the .env file

```bash
echo "CERT_PUB_KEY=$(sudo base64 -w 0 /etc/letsencrypt/live/${rootdomain}/fullchain.pem)" >> .env
echo "CERT_PRIV_KEY=$(sudo base64 -w 0 /etc/letsencrypt/live/${rootdomain}/privkey.pem)" >> .env
```

!!!warning 
    You must remove the old and any duplicate entries for CERT_PUB_KEY and CERT_PRIV_KEY in the .env file

Now run `sudo docker-compose restart` and the new certificate will be in effect
