# Troubleshooting

#### "Bad credentials" error when trying to login to the Web UI

If you are sure you are using the correct credentials and still getting a "bad credentials" error, open your browser's dev tools (ctrl + shift + j on chrome) and check the Console tab to see the real error.

It will most probably be a CORS error which means you need to check your DNS settings and make sure whatever computer you're trying to access the UI from resolves your 3 subdomains to the correct IP of the server running the RMM (public IP if running in the cloud, or private IP if running behind NAT).

If you see an error about SSL or certificate expired, then your Let's Encrypt cert has probably expired and you'll need to renew it.

Refer to the Let's Encrypt cert renewal instructions [here](update_server.md#keeping-your-lets-encrypt-certificate-up-to-date)

<br/>

#### Agents not updating

The most common problem we've seen of agents not updating is due to Antivirus blocking the updater executable.

Windows Defender will 100% of the time block the updater from running unless an exclusion is set.

Refer to the [Agent Installation](install_agent.md) instructions for AV exceptions to set and manually doing an agent update with logging to troubleshoot further.

Agents will also not automatically update if they are too old.

Since Tactical RMM is still in alpha and the developers makes breaking changes pretty frequently, there is no promise of backwards compatibility.

If you have agents that are relatively old, you will need to uninstall them manually and reinstall using the latest version.

<br/>

#### Agents not checking in or showing up / General agent issues

First, reload NATS from tactical's web UI:<br />
*Tools > Server Maintenance > Reload Nats Configuration*

Open CMD as admin on the problem computer and stop the agent services:

```cmd
net stop tacticalagent
net stop tacticalrpc
```

Run the tacticalagent service manually with debug logging:
```cmd
"C:\Program Files\TacticalAgent\tacticalrmm.exe" -m winagentsvc -log debug -logto stdout
```

Run the tacticalrpc service manually with debug logging:
```cmd
"C:\Program Files\TacticalAgent\tacticalrmm.exe" -m rpc -log debug -logto stdout
```

This will print out a ton of info. You should be able to see the error from the debug log output.

Please then copy/paste the logs and post them either in our [Discord support chat](https://discord.gg/upGTkWp), or create a [github issue](https://github.com/wh1te909/tacticalrmm/issues).

If all else fails, simply uninstall the agent either from control panel or silently with `"C:\Program Files\TacticalAgent\unins000.exe" /VERYSILENT` and then reinstall the agent.

#### All other errors

First, run the [update script](update_server.md#updating-to-the-latest-rmm-version) with the `--force` flag. <br/>This will fix permissions and reinstall python/node packages that might have gotten corrupted.

```bash
./update.sh --force
```

Check the debug log from the web UI: **File > Debug Log**

Open your browser's dev tools (ctrl + shift + j on chrome) and check the Console tab for any errors

Check all the systemd services that the rmm uses to function and check to make sure they're all active/running and enabled:

```bash
sudo systemctl status rmm
sudo systemctl status daphne
sudo systemctl status celery
sudo systemctl status celerybeat
sudo systemctl status nginx
sudo systemctl status nats
sudo systemctl status meshcentral
sudo systemctl status mongod
sudo systemctl status postgresql
sudo systemctl status redis
```

Read through the log files in the following folders and check for errors:
```bash
/rmm/api/tacticalrmm/tacticalrmm/private/log
/var/log/celery
```




