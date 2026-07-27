"""Derive "how long does this job take" from closed, hand-worked, non-alert tickets.

The baseline for time-saved has to come from somewhere defensible. It is sitting in history:
tickets that were CLOSED, were NOT machine alerts, and were worked by a person - their message
bursts say how long that class of job actually took. Group those by the procedure that matches
the ticket, take the MEDIAN (not the mean - one 4-hour outlier should not set the standard),
and that is the baseline.

Only writes a baseline where there is enough evidence, and records how many tickets it came
from so the number can be challenged.
"""

import statistics
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Derive AIProcedure.baseline_minutes from closed non-alert tickets"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=120)
        parser.add_argument("--min-samples", type=int, default=3)
        parser.add_argument("--commit", action="store_true")
        parser.add_argument("--overwrite", action="store_true",
                            help="replace baselines that are already set")

    def handle(self, *a, **o):
        import requests as _requests
        from django.conf import settings

        from core.ai_match import match_procedures
        from core.models import AIProcedure, CoreSettings
        from core.work_ledger import caps_from_settings, sessionize_staff_events

        core = CoreSettings.objects.first()
        caps = caps_from_settings(core)
        bridge = getattr(settings, "PI_BRIDGE_URL", "http://127.0.0.1:8787")
        r = _requests.post(f"{bridge}/pi/helpdesk-op", json={
            "operation": "ticket_message_events",
            "args": {"hours": o["days"] * 24, "all_teams": True, "closed_only": True},
            "helpdesk_api": {"base_url": core.ai_helpdesk_api_base_url or "",
                             "api_key": core.ai_helpdesk_api_key or ""},
            "helpdesk_code": core.ai_helpdesk_code or "",
        }, timeout=(10, 900)).json()
        rows = r.get("result") or []
        self.stdout.write(f"closed tickets in {o['days']}d: {len(rows)}")

        samples = {}          # procedure id -> [minutes]
        titles = {}
        unmatched_minutes = []
        for t in rows:
            if t.get("is_alert"):
                continue      # machine alerts are not "jobs"; they are noise with a verdict
            staff_msgs = [e for e in (t.get("events") or []) if e.get("kind") == "staff"]
            # ONLY tickets where the messaging tracks the work. A tech who spends 45 minutes
            # building something and writes one closing note scores 4 minutes - the floor of
            # lead-in + tail - so single- and double-message tickets would drag every baseline
            # down to nothing. Three or more staff messages means the conversation moved with
            # the job. Even then this is a LOWER BOUND, and it is labelled as one.
            if len(staff_msgs) < 3:
                continue
            bursts = sessionize_staff_events(t.get("events") or [], caps)
            if not bursts:
                continue      # nobody visibly worked it by hand
            total = 0.0
            for _actor, bs in bursts.items():
                for start, end, n in bs:
                    total += (end - start).total_seconds() / 60 + caps["lead_in"] + caps["tail"]
            if total <= 0:
                continue
            hits = match_procedures(t.get("subject", ""), t.get("body", ""), limit=1)
            if hits:
                samples.setdefault(hits[0]["id"], []).append(total)
                titles[hits[0]["id"]] = hits[0]["title"]
            else:
                unmatched_minutes.append(total)

        wrote = 0
        self.stdout.write("\nderived baselines (median hand-worked minutes):")
        for pid, vals in sorted(samples.items(), key=lambda kv: -len(kv[1])):
            if len(vals) < o["min_samples"]:
                continue
            med = round(statistics.median(vals), 1)
            p = AIProcedure.objects.filter(id=pid).first()
            if not p:
                continue
            skip = (p.baseline_minutes is not None and not o["overwrite"])
            self.stdout.write(
                f"  #{pid:<4} {titles[pid][:52]:52} n={len(vals):3} median={med:6.1f}m"
                f"  range {min(vals):.0f}-{max(vals):.0f}" + ("   [kept existing]" if skip else ""))
            if o["commit"] and not skip:
                p.baseline_minutes = med
                p.save(update_fields=["baseline_minutes"])
                self.stdout.write(self.style.WARNING(
                    f"        -> baseline set from {len(vals)} hand-worked tickets (LOWER BOUND: "
                    f"derived from message timing, which cannot see work done off-ticket)"))
                wrote += 1

        if unmatched_minutes:
            med = round(statistics.median(unmatched_minutes), 1)
            self.stdout.write(f"\nno procedure matched: {len(unmatched_minutes)} tickets, "
                              f"median {med}m - that is the fleet-wide fallback for unclassified work")
        self.stdout.write(self.style.SUCCESS(
            f"\n{'wrote' if o['commit'] else 'would write'} {wrote} baseline(s)"))
