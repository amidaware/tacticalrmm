"""Attach the User FK to every historical ledger row, and report anything unlinkable.

Backfill for the identity change: rows were keyed on a username string, which is mutable. Once
each row points at a user id, a rename is just a display change and history stops forking.
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Backfill TicketWorkEntry.actor_user / AIActionCredit.actor_user"

    def add_arguments(self, parser):
        parser.add_argument("--commit", action="store_true")

    def handle(self, *a, **o):
        from core.models import AIActionCredit, TicketWorkEntry
        from core.work_ledger import actor_index, canonical_actor
        from accounts.models import User

        by_name, aliases = actor_index()
        users = {u.username: u for u in User.objects.all()}
        stats = {"linked": 0, "already": 0, "unlinkable": {}}

        for model, label in ((TicketWorkEntry, "work entries"), (AIActionCredit, "action credits")):
            for row in model.objects.filter(actor_user__isnull=True):
                raw = row.actor_username or row.actor_display
                uname, disp = canonical_actor(raw, by_name, aliases)
                u = users.get(uname)
                if not u:
                    stats["unlinkable"][raw] = stats["unlinkable"].get(raw, 0) + 1
                    continue
                if o["commit"]:
                    row.actor_user = u
                    row.actor_username = u.username
                    row.actor_display = u.get_full_name() or u.username
                    row.save(update_fields=["actor_user", "actor_username", "actor_display"])
                stats["linked"] += 1
            stats["already"] += model.objects.filter(actor_user__isnull=False).count()

        self.stdout.write(f"{'linked' if o['commit'] else 'would link'}: {stats['linked']} rows")
        for k, n in sorted(stats["unlinkable"].items(), key=lambda x: -x[1]):
            self.stdout.write(self.style.WARNING(f"  {n:4} rows have no matching user: '{k}'"))
