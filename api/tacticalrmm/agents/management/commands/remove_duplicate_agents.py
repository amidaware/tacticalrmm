import asyncio
from collections import defaultdict
from datetime import datetime, timezone

from django.core.management.base import BaseCommand

from agents.models import Agent
from tacticalrmm.utils import reload_nats


class Command(BaseCommand):
    help = "Remove duplicate agents based on serial number or hostname, keeping the most recently seen agent"

    def add_arguments(self, parser):
        # Create mutually exclusive group for deduplication key
        key_group = parser.add_mutually_exclusive_group()
        key_group.add_argument(
            "--serialnumber",
            action="store_true",
            help="Remove duplicates based on serial number (default)",
        )
        key_group.add_argument(
            "--hostname",
            action="store_true",
            help="Remove duplicates based on hostname",
        )

        parser.add_argument(
            "--delete",
            action="store_true",
            help="Actually delete duplicate agents (without this flag, only shows what would be deleted)",
        )
        parser.add_argument(
            "--ignore-empty-serial",
            action="store_true",
            help="Skip agents with empty/missing serial numbers (only applies when using --serialnumber)",
        )

    def handle(self, *args, **kwargs):
        delete = kwargs["delete"]
        ignore_empty_serial = kwargs["ignore_empty_serial"]
        use_hostname = kwargs["hostname"]
        use_serialnumber = kwargs["serialnumber"]

        # Default to serial number if neither specified
        if not use_hostname and not use_serialnumber:
            use_serialnumber = True

        dedup_key = "hostname" if use_hostname else "serial number"
        self.stdout.write(f"Scanning for duplicate agents by {dedup_key}...")

        # Get all agents
        agents = Agent.objects.select_related("site__client").all()

        # Group agents by the selected key
        key_groups = defaultdict(list)
        empty_key_agents = []  # Track agents with empty/missing key values

        for agent in agents:
            if use_hostname:
                # Group by hostname
                hostname = agent.hostname
                if not hostname or hostname == "":
                    empty_key_agents.append(agent)
                else:
                    key_groups[hostname].append(agent)
            else:
                # Group by serial number
                serial = agent.serial_number

                # Handle agents with no serial number
                if not serial or serial == "":
                    if not ignore_empty_serial:
                        empty_key_agents.append(agent)
                    continue

                key_groups[serial].append(agent)

        # Report agents with empty key values
        if empty_key_agents:
            self.stdout.write(
                self.style.WARNING(
                    f"\nFound {len(empty_key_agents)} agents with empty {dedup_key}:"
                )
            )
            for agent in empty_key_agents:
                msg = (
                    f"  {agent.hostname} | "
                    f"Last Seen: {agent.last_seen} | "
                    f"Version: {agent.version} | "
                    f"{agent.client} > {agent.site}"
                )
                self.stdout.write(self.style.WARNING(msg))
            self.stdout.write("")  # Empty line for readability

        # Find duplicates (keys with more than one agent)
        duplicates = {
            key: agents_list
            for key, agents_list in key_groups.items()
            if len(agents_list) > 1
        }

        if not duplicates and not empty_key_agents:
            self.stdout.write(
                self.style.SUCCESS(
                    f"No duplicate agents found! (Scanned {len(agents)} agents)"
                )
            )
            return

        if not duplicates:
            self.stdout.write(
                self.style.SUCCESS(
                    f"No duplicate agents found by {dedup_key}! (Scanned {len(agents)} agents)"
                )
            )
            return

        self.stdout.write(
            self.style.WARNING(
                f"Found {len(duplicates)} {dedup_key}s with duplicate agents:"
            )
        )

        total_to_delete = 0
        deleted_count = 0

        for key, agent_list in duplicates.items():
            # Sort by last_seen, most recent first (None values go to end)
            sorted_agents = sorted(
                agent_list,
                key=lambda a: a.last_seen if a.last_seen else datetime.min.replace(tzinfo=timezone.utc),
                reverse=True,
            )

            # Keep the most recently seen agent
            keep_agent = sorted_agents[0]
            delete_agents = sorted_agents[1:]

            total_to_delete += len(delete_agents)

            # Display appropriate header based on deduplication key
            if use_hostname:
                header = f"Hostname: {key} ({len(agent_list)} duplicates found)"
            else:
                header = f"Serial: {key} ({len(agent_list)} duplicates found)"

            self.stdout.write(self.style.WARNING(header))

            # Show which agent we're keeping
            keep_msg = (
                f"  Keeping: {keep_agent.hostname} | "
                f"Last Seen: {keep_agent.last_seen} | "
                f"Version: {keep_agent.version} | "
                f"{keep_agent.client} > {keep_agent.site}"
            )
            self.stdout.write(self.style.SUCCESS(keep_msg))

            # Process agents to delete
            for agent in delete_agents:
                msg = (
                    f"  Deleting: {agent.hostname} | "
                    f"Last Seen: {agent.last_seen} | "
                    f"Version: {agent.version} | "
                    f"{agent.client} > {agent.site}"
                )

                if delete:
                    self.stdout.write(self.style.SUCCESS(msg))
                    # Send uninstall command (fire and forget)
                    try:
                        asyncio.run(agent.nats_cmd({"func": "uninstall"}, wait=False))
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(
                                f"    Warning: Could not send uninstall command: {e}"
                            )
                        )

                    # Delete the agent
                    try:
                        agent.delete()
                        deleted_count += 1
                    except Exception as e:
                        err = f"    Failed to delete agent {agent.hostname}: {e}"
                        self.stdout.write(self.style.ERROR(err))
                else:
                    self.stdout.write(self.style.WARNING(msg))

        # Calculate summary statistics
        num_devices_with_dupes = len(duplicates)
        total_agent_records = num_devices_with_dupes + total_to_delete

        if delete:
            # Reload NATS configuration
            reload_nats()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Found duplicates for {num_devices_with_dupes} devices ({total_agent_records} total agent records)\n"
                    f"Kept {num_devices_with_dupes} most recent agents, deleted {deleted_count} older duplicates"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Found duplicates for {num_devices_with_dupes} devices ({total_agent_records} total agent records)\n"
                    f"Keeping {num_devices_with_dupes} most recent agents, deleting {total_to_delete} older duplicates. "
                    "Run again with --delete to actually delete them."
                )
            )

        if use_serialnumber and ignore_empty_serial:
            # Count how many agents were skipped due to empty serial
            skipped_count = len([a for a in agents if not a.serial_number or a.serial_number == ""])
            if skipped_count > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f"\nNote: {skipped_count} agents without serial numbers were ignored "
                        "(run without --ignore-empty-serial to see these agents)"
                    )
                )
