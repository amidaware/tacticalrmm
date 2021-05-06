# Unsupported Reference scripts

!!!note 
    These are not supported scripts/configurations by Tactical RMM, but it's provided here for your reference. 

## HAProxy


Check/Change the mesh central config.json, some of the values may be set already, CertUrl must be changed to point to the HAProxy server.

### Meshcentral Adjustment

Credit to [@bradhawkins](https://github.com/bradhawkins85)

Edit Meshcentral config

```bash
nano /meshcentral/meshcentral-data/config.json
```

Insert this (modify `HAProxyIP` to your network)

```
{
  "settings": {
    "Port": 4430,
    "AliasPort": 443,
    "RedirPort": 800,
    "TlsOffload": "127.0.0.1",
  },
  "domains": {
    "": {
      "CertUrl": "https://HAProxyIP:443/",
    }
  }
}
```

Restart meshcentral

```bash
service meshcentral restart
```

### HAProxy Config

The order of use_backend is important `Tactical-Mesh-WebSocket_ipvANY` must be before `Tactical-Mesh_ipvANY`
The values of `timeout connect`, `timeout server`, `timeout tunnel` in `Tactical-Mesh-WebSocket` have been configured to maintain a stable agent connection, however you may need to adjust these values to suit your environment. 

```
frontend HTTPS-merged
	bind			0.0.0.0:443 name 0.0.0.0:443   ssl crt-list /var/etc/haproxy/HTTPS.crt_list  #ADJUST THIS TO YOUR OWN SSL CERTIFICATES
	mode			http
	log			global
	option			socket-stats
	option			dontlognull
	option			http-server-close
	option			forwardfor
	acl https ssl_fc
	http-request set-header		X-Forwarded-Proto http if !https
	http-request set-header		X-Forwarded-Proto https if https
	timeout client		30000
	acl			RMM	var(txn.txnhost) -m sub -i rmm.example.com
	acl			aclcrt_RMM	var(txn.txnhost) -m reg -i ^([^\.]*)\.example\.com(:([0-9]){1,5})?$
	acl			API	var(txn.txnhost) -m sub -i api.example.com
	acl			aclcrt_API	var(txn.txnhost) -m reg -i ^([^\.]*)\.example\.com(:([0-9]){1,5})?$
	acl			is_websocket	hdr(Upgrade) -i WebSocket
	acl			is_mesh	var(txn.txnhost) -m beg -i mesh.example.com
	acl			aclcrt_MESH-WebSocket	var(txn.txnhost) -m reg -i ^([^\.]*)\.example\.com(:([0-9]){1,5})?$
	acl			MESH	var(txn.txnhost) -m sub -i mesh.example.com
	acl			aclcrt_MESH	var(txn.txnhost) -m reg -i ^([^\.]*)\.example\.com(:([0-9]){1,5})?$
	#PUT OTHER USE_BACKEND IN HERE
	use_backend Tactical_ipvANY  if  RMM aclcrt_RMM
	use_backend Tactical_ipvANY  if  API aclcrt_API
	use_backend Tactical-Mesh-WebSocket_ipvANY  if  is_websocket is_mesh aclcrt_MESH-WebSocket
	use_backend Tactical-Mesh_ipvANY  if  MESH aclcrt_MESH

frontend http-to-https
	bind			0.0.0.0:80   
	mode			http
	log			global
	option			http-keep-alive
	timeout client		30000
	http-request redirect scheme https 


backend Tactical_ipvANY
	mode			http
	id			100
	log			global
	timeout connect		30000
	timeout server		30000
	retries			3
	option			httpchk GET / 
	server			tactical 192.168.10.123:443 id 101 ssl check inter 1000  verify none 


backend Tactical-Mesh-WebSocket_ipvANY
	mode			http
	id			113
	log			global
	timeout connect		3000
	timeout server		3000
	retries			3
	timeout tunnel		3600000
	http-request add-header X-Forwarded-Host %[req.hdr(Host)] 
	http-request add-header X-Forwarded-Proto https 
	server			tactical 192.168.10.123:443 id 101 ssl  verify none 

backend Tactical-Mesh_ipvANY
	mode			http
	id			112
	log			global
	timeout connect		15000
	timeout server		15000
	retries			3
	option			httpchk GET / 
	timeout tunnel		15000
	http-request add-header X-Forwarded-Host %[req.hdr(Host)] 
	http-request add-header X-Forwarded-Proto https 
	server			tactical 192.168.10.123:443 id 101 ssl check inter 1000  verify none 
```

## fail2ban

### Install fail2ban

```bash
sudo apt install -y fail2ban
```

### Set Tactical fail2ban filter conf File


```
tacticalfail2banfilter="$(cat << EOF
[Definition]
failregex = ^<HOST>.*400.17.*$
ignoreregex = ^<HOST>.*200.*$
EOF
)"
sudo echo "${tacticalfail2banfilter}" > /etc/fail2ban/filter.d/tacticalrmm.conf
```

### Set Tactical fail2ban jail conf File

```
tacticalfail2banjail="$(cat << EOF
[tacticalrmm]
enabled = true
port = 80,443
filter = tacticalrmm
action = iptables-allports[name=tactical]
logpath = /rmm/api/tacticalrmm/tacticalrmm/private/log/access.log
maxretry = 3
bantime = 14400
findtime = 14400
EOF
)"
sudo echo "${tacticalfail2banjail}" > /etc/fail2ban/jail.d/tacticalrmm.local
```

### Restart fail2ban

```bash
sudo systemctl restart fail2ban
```