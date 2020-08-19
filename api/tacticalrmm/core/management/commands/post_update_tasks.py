import os
import subprocess
from time import sleep

from django.core.management.base import BaseCommand

from agents.models import Agent


class Command(BaseCommand):
    help = "Collection of tasks to run after updating the rmm, after migrations"

    def handle(self, *args, **kwargs):
        # sync modules. split into chunks of 30 agents to not overload the salt master
        agents = Agent.objects.all()
        online = [i.salt_id for i in agents if i.status == "online"]

        chunks = (online[i : i + 30] for i in range(0, len(online), 30))

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
