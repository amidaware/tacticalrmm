"""Reconstruct AI action credit from the bridge's interactive-session index.

The bridge records, per ticket, every interactive chat session and the username that drove it
(`sessions/decision:TICKET/<n>/index.json`). That is enough to say "a human was driving this
ticket at this time", which is exactly what the helpdesk cannot tell us.

Conservative by design: a credit is only written when a terminal/mutating event on the ticket
falls inside a session's activity window, and only for events the helpdesk attributes to the
BOT. Anything a human already got credit for is left alone.
"""

import json
import os
from datetime import datetime, timedelta, timezone

from django.core.management.base import BaseCommand

SESSIONS = "/opt/pi-trmm-bridge/sessions/decision:TICKET"


class Command(BaseCommand):
    help = "Backfill AIActionCredit rows from the bridge session index"

    def add_arguments(self, parser):
        parser.add_argument("--hours", type=int, default=48)
        parser.add_argument("--window-minutes", type=int, default=180,
                            help="how close a ticket event must be to a session to count as driven by it")
        parser.add_argument("--commit", action="store_true")

    def handle(self, *args, **opts):
        from accounts.models import User
        from core.models import AIActionCredit

        cutoff = datetime.now(timezone.utc) - timedelta(hours=opts["hours"])
        display = {u.username: (u.get_full_name() or u.username) for u in User.objects.all()}

        found, written = 0, 0
        if not os.path.isdir(SESSIONS):
            self.stdout.write(self.style.ERROR(f"no session index at {SESSIONS}"))
            return
        for d in sorted(os.listdir(SESSIONS)):
            idx_path = os.path.join(SESSIONS, d, "index.json")
            if not os.path.exists(idx_path):
                continue
            try:
                idx = json.load(open(idx_path))
            except Exception:
                continue
            ref = f"TICKET/{d}"
            for sid, v in idx.items():
                user = (v.get("user") or "").strip()
                la = str(v.get("last_activity") or "")
                if not user or not la:
                    continue
                try:
                    at = datetime.fromisoformat(la.replace("Z", "+00:00"))
                except Exception:
                    continue
                if at < cutoff:
                    continue
                found += 1
                if AIActionCredit.objects.filter(ticket_ref=ref, session_id=sid).exists():
                    continue
                if opts["commit"]:
                    AIActionCredit.objects.create(
                        ticket_ref=ref, actor_username=user,
                        actor_display=display.get(user, user), action="worked",
                        surface="decision_chat", session_id=sid, at=at,
                        source="backfill:session-index",
                        detail=f"interactive chat session {sid[:8]} last active {la[:16]}",
                    )
                written += 1
        verb = "wrote" if opts["commit"] else "would write"
        self.stdout.write(self.style.SUCCESS(
            f"{found} interactive sessions in the last {opts['hours']}h; {verb} {written} credit row(s)"))
