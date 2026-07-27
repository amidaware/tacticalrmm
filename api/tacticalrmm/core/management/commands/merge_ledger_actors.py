"""Re-resolve every ledger row's actor to the canonical person.

Renames and duplicate accounts fork a person's history. This is an attribution correction, not
a time correction - the same work, by the same human, under a label that has changed - so rows
are updated in place and stamped with what was changed. Time values are never touched.
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Re-resolve ledger actors through aliases and canonical accounts"

    def add_arguments(self, parser):
        parser.add_argument("--commit", action="store_true")

    def handle(self, *a, **o):
        from core.models import TicketWorkEntry
        from core.work_ledger import actor_index, canonical_actor

        by_name, aliases = actor_index()
        changed, unresolved = {}, {}
        for e in TicketWorkEntry.objects.all():
            raw = e.actor_username or e.actor_display
            uname, disp = canonical_actor(raw, by_name, aliases)
            if not uname:
                unresolved[e.actor_display or raw] = unresolved.get(e.actor_display or raw, 0) + 1
                continue
            if uname != e.actor_username or disp != e.actor_display:
                key = f"{e.actor_username or '(blank)'}/{e.actor_display} -> {uname}/{disp}"
                changed[key] = changed.get(key, 0) + 1
                if o["commit"]:
                    was = f"{e.actor_username or '(blank)'}/{e.actor_display}"
                    e.actor_username, e.actor_display = uname, disp
                    e.note = (e.note + " | " if e.note else "") + f"actor re-resolved from {was}"
                    e.save(update_fields=["actor_username", "actor_display", "note"])
        for k, n in sorted(changed.items(), key=lambda x: -x[1]):
            self.stdout.write(f"  {n:4} rows  {k}")
        for k, n in sorted(unresolved.items(), key=lambda x: -x[1]):
            self.stdout.write(self.style.WARNING(f"  {n:4} rows  UNRESOLVED actor '{k}'"))
        self.stdout.write(self.style.SUCCESS(
            f"{'applied' if o['commit'] else 'dry run'}: {sum(changed.values())} rows re-attributed"))
