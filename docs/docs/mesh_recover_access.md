# Recover Mesh Central Login Credentials

#### Get Mesh Central Admin Login

When logged into Tactical RMM goto:

Settings Menu > global settings > meshcentral tab > Username

#### Reset password for that account

The login to SSH on TRMM server and set password

```bash
cd /meshcentral/
sudo systemctl stop meshcentral
node node_modules/meshcentral --resetaccount <username> --pass <password>
sudo systemctl start meshcentral```
