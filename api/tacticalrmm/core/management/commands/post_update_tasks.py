import os
import shutil
import subprocess
import sys
import tempfile
from time import sleep

from django.core.management.base import BaseCommand

from agents.models import Agent
from scripts.models import Script


class Command(BaseCommand):
    help = "Collection of tasks to run after updating the rmm, after migrations"

    def handle(self, *args, **kwargs):

        if not os.path.exists("/usr/local/bin/goversioninfo"):
            self.stdout.write(self.style.ERROR("*" * 100))
            self.stdout.write("\n")
            self.stdout.write(
                self.style.ERROR(
                    "ERROR: New update script available. Delete this one and re-download."
                )
            )
            self.stdout.write("\n")
            sys.exit(1)

        # 10-16-2020 changed the type of the agent's 'disks' model field
        # from a dict of dicts, to a list of disks in the golang agent
        # the following will convert dicts to lists for agent's still on the python agent
        agents = Agent.objects.all()
        for agent in agents:
            if agent.disks is not None and isinstance(agent.disks, dict):
                new = []
                for k, v in agent.disks.items():
                    new.append(v)

                agent.disks = new
                agent.save(update_fields=["disks"])
                self.stdout.write(
                    self.style.SUCCESS(f"Migrated disks on {agent.hostname}")
                )

        # sync modules. split into chunks of 60 agents to not overload the salt master
        agents = Agent.objects.all()
        online = [i.salt_id for i in agents if i.status == "online"]

        chunks = (online[i : i + 60] for i in range(0, len(online), 60))

        self.stdout.write(self.style.SUCCESS("Syncing agent modules..."))
        for chunk in chunks:
            r = Agent.salt_batch_async(minions=chunk, func="saltutil.sync_modules")
            sleep(5)

        has_old_config = True
        rmm_conf = "/etc/nginx/sites-available/rmm.conf"
        if os.path.exists(rmm_conf):
            with open(rmm_conf) as f:
                for line in f:
                    if "location" and "builtin" in line:
                        has_old_config = False
                        break

        if has_old_config:
            new_conf = """
            location /builtin/ {
                internal;
                add_header "Access-Control-Allow-Origin" "https://rmm.yourwebsite.com";
                alias /srv/salt/scripts/;
            }
            """

            after_this = """
            location /saltscripts/ {
                internal;
                add_header "Access-Control-Allow-Origin" "https://rmm.yourwebsite.com";
                alias /srv/salt/scripts/userdefined/;
            }
            """

            self.stdout.write(self.style.ERROR("*" * 100))
            self.stdout.write("\n")
            self.stdout.write(
                self.style.ERROR(
                    "WARNING: A recent update requires you to manually edit your nginx config"
                )
            )
            self.stdout.write("\n")
            self.stdout.write(
                self.style.ERROR("Please add the following location block to ")
                + self.style.WARNING(rmm_conf)
            )
            self.stdout.write(self.style.SUCCESS(new_conf))
            self.stdout.write("\n")
            self.stdout.write(
                self.style.ERROR(
                    "You can paste the above right after the following block that's already in your nginx config:"
                )
            )
            self.stdout.write(after_this)
            self.stdout.write("\n")
            self.stdout.write(
                self.style.ERROR(
                    "Make sure to replace rmm.yourwebsite.com with your domain"
                )
            )
            self.stdout.write(
                self.style.ERROR("After editing, restart nginx with the command ")
                + self.style.WARNING("sudo systemctl restart nginx")
            )
            self.stdout.write("\n")
            self.stdout.write(self.style.ERROR("*" * 100))
            input("Press Enter to continue...")

        # install go
        if not os.path.exists("/usr/local/rmmgo/"):
            self.stdout.write(self.style.SUCCESS("Installing golang"))
            subprocess.run("sudo mkdir -p /usr/local/rmmgo", shell=True)
            tmpdir = tempfile.mkdtemp()
            r = subprocess.run(
                f"wget https://golang.org/dl/go1.15.linux-amd64.tar.gz -P {tmpdir}",
                shell=True,
            )

            gotar = os.path.join(tmpdir, "go1.15.linux-amd64.tar.gz")

            subprocess.run(f"tar -xzf {gotar} -C {tmpdir}", shell=True)

            gofolder = os.path.join(tmpdir, "go")
            subprocess.run(f"sudo mv {gofolder} /usr/local/rmmgo/", shell=True)
            shutil.rmtree(tmpdir)

        # load community scripts into the db
        Script.load_community_scripts()
