
# TacticalRMM behind Nginx Proxy Manager
### Tested and working on the following:
## ✅ TRMM hosted on Ubuntu 22.04 via Proxmox VM
## ✅ Nginx Proxy Manager hosted on Debian 11 via Proxmox CT W/ Docker

#### ***We'll use "YOURDOMAIN" in place of your actual domain name***

## Step 1

First and foremost, you need to disable Nginx Proxy Manager. To do this, on your routers firewall settings, forward ports 443 and 80 to the local ip that will be running your TRMM instance.
This is only temporary as we want to make sure we can get TRMM installed and running with a STANDARD install FIRST.
You will also need to make sure the following subdomains are pointing to your external IP:

> api.YOURDOMAIN.com
> 
> rmm.YOURDOMAIN.com
> 
> mesh.YOURDOMAIN.com

Use 

    curl icanhazip.com    
    
to pull your external IP if you don't know it.

Once you have ports 443 and 80 forwarded correctly, go ahead and run a STANDARD install of TRMM on a FRESH machine. You can find the Install Documentation [here](https://docs.tacticalrmm.com/install_server/#installation).


## Step 2
# Nginx Proxy Manager Proxy Host Configuration
<br> 

Assuming you installed TRMM properly and all of its features are working correctly, we will now get into setting up Nginx Proxy Manager to work with TRMM. Go ahead and forward ports 443 and 80 back to your Nginx Proxy Manager instance.
<br>
<br>

Below you will find the 3 different Proxy Hosts you need to create on Nginx Proxy Manager.

# "API" Domain
### Details Tab:

##### **Domain Name:** --> api.YOURDOMAIN.com

##### **Scheme:** --> https

##### **Forward Hostname / IP:** --> The Local IP of your TRMM instance. ie: 192.168.1.155

##### **Forward Port:** --> 443

##### **Enabled Options:**

   Cache Assets;
   Block Common Exploits;
   Websockets Support

##### **Access List:** --> Publicly Accessible


<br>
<br>

# "MESH" Domain
### Details Tab:

##### **Domain Name:** --> mesh.YOURDOMAIN.com

##### **Scheme:** --> http

##### **Forward Hostname / IP:** --> The Local IP of your TRMM instance. ie: 192.168.1.155

##### **Forward Port:** --> 4430

##### **Enabled Options:**

   Block Common Exploits;
   Websockets Support

##### **Access List:** --> Publicly Accessible

### Advanced Tab:

##### **Custom Nginx Configuration**

    proxy_set_header Host $host;
    proxy_set_header CF-Connecting-IP $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Host $host:$server_port;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;


<br>
<br>

# "RMM" Domain
### Details Tab:

##### **Domain Name:** --> rmm.YOURDOMAIN.com

##### **Scheme:** --> https

##### **Forward Hostname / IP:** --> The Local IP of your TRMM instance. ie: 192.168.1.155

##### **Forward Port:** --> 443

##### **Enabled Options:**

   Cache Assets;
   Block Common Exploits;
   Websockets Support

##### **Access List:** --> Publicly Accessible

<br>
<br>

# NPM SSL Configuration

In order for TRMM to work properly with NPM, you'll need to create a wildcard or multi-domain SSL Certificate.

<br>

To do this, on the Nginx Proxy Manager Dashboard, click the *SSL Certificates* tab.

<br>

![SSL Cert Tab On Nginx Proxy Manager](https://i.imgur.com/pVGrg3l.png)

<br>


Now in the top right, click "Add SSL Certificate". Select "Let's Encrypt".

<br>

![Add SSL Cert On Nginx Proxy Manager](https://i.imgur.com/ijTsVjo.png)

<br>

Add each of the domains listed above to the "Domain Names" field. Make sure you add them 1 at a time and click the dropdown of the domain to add it. Once you've added all 3 domains, enable the "I agree" tick and click save.

<br>

You should now see something like this in your list of SSL Certs:

<br>

![Multidomain SSL Cert On Nginx Proxy Manager](https://i.imgur.com/Sv0SW0m.png)

<br>

Go ahead and download this certificate by clicking the 3 dots to the right of the cert entry and click "Download".

<br>

I suggest you follow [these](https://docs.tacticalrmm.com/unsupported_scripts/#using-purchased-ssl-certs-instead-of-lets-encrypt-wildcards) instructions for adding the new certs to your TRMM instance.

<br>
<br>


# MeshCentral Configuration

Now you should have Nginx Proxy Manager completely setup. Lets move on to the MeshCentral Configuration.

<br>

First, cd to

    /meshcentral/meshcentral-data

<br>
Now edit the file named "config.json".

<br>
Make sure your config file looks like the one shown below.

<br>

    {
      "settings": {
        "cert": "mesh.YOURDOMAIN.com",
        "WANonly": true,
        "minify": 1,
        "port": 4430,
        "aliasPort": 443,
        "redirPort": 800,
        "allowLoginToken": true,
        "allowFraming": true,
        "agentPing": 35,
        "agentPong": 300,
        "allowHighQualityDesktop": true,
        "tlsOffload": "Nginx Proxy Manager Local IP",
        "trustedProxy": "Nginx Proxy Manager Local IP",
        "agentCoreDump": false,
        "compression": true,
        "wsCompression": true,
        "agentWsCompression": true,
        "postgres": {
          "user": "REDACTED",
          "password": "REDACTED",
          "port": "5432",
          "host": "localhost"
        },
        "MaxInvalidLogin": {
          "time": 5,
          "count": 5,
          "coolofftime": 30
        }
      },
      "domains": {
        "": {
          "title": "Tactical RMM",
          "title2": "Tactical RMM",
          "newAccounts": false,
          "certUrl": "https://mesh.YOURDOMAIN.com:443/",
          "geoLocation": true,
          "cookieIpCheck": false,
          "mstsc": true
        }
      }
    }

<br>
<br>

If you want to enable logging in case anything goes wrong during this process, follow the instructions [here](https://ylianst.github.io/MeshCentral/meshcentral/debugging/#logging-it-all).

<br>
<br>

As of now, everything should be working. If you have any issues, feel free to join the [discord](https://discord.com/invite/upGTkWp).

# Keep in mind, this is considered an **UNSUPPORTED** installation. Developers are not obligated to fix any issues you may encounter. Good luck.