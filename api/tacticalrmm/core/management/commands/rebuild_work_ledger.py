"""Rebuild the work ledger from interactive-session transcripts.

Idempotent: a session already in the ledger is skipped, so this can be re-run safely.
Nothing is deleted - corrections belong in new rows (TicketWorkEntry.superseded_by).
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Rebuild TicketWorkEntry rows from bridge session transcripts"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=14)
        parser.add_argument("--commit", action="store_true")
        parser.add_argument("--quiet-rows", action="store_true", help="skip the per-row listing")

    def handle(self, *args, **o):
        from accounts.models import User

        from core.models import CoreSettings, TicketWorkEntry
        from core.work_ledger import (burst_minutes, caps_from_settings, is_real_work,
                                      iter_sessions, mark_overlaps, method_label,
                                      read_transcript, split_bursts)

        from core.work_ledger import actor_index, canonical_actor

        core = CoreSettings.objects.first()
        caps = caps_from_settings(core)
        by_name, aliases = actor_index()

        def resolve(raw):
            cu, cd = canonical_actor(raw, by_name, aliases)
            return (cu or raw), (cd or raw), User.objects.filter(username=cu).first() if cu else None
        sessions = iter_sessions(o["days"])

        made, skipped_existing, skipped_nowork, no_transcript = [], 0, 0, 0
        for s in sessions:
            if not s["user"] or s["user"] == "test":
                continue
            # A ticket chat RESUMES the same transcript file under a new session id, so one
            # file can appear under several ids in the index. Keying dedupe on session id
            # therefore re-imported the same bursts once per id and double-counted the work
            # (15.3 h of it, before this was caught). The burst itself is the identity.
            pass
            tr = read_transcript(s["file"])
            if tr and is_real_work(tr):
                # ONE ENTRY PER WORK BURST, not per transcript: a file can span days.
                bursts = split_bursts(tr["events"], caps["idle_cap"])
                user_set = set(tr["user_turns"])
                for bi, burst in enumerate(bursts):
                    # A burst with no human turn in it is the AI finishing on its own after the
                    # person left; it is not their attention time.
                    if not any(t in user_set for t in burst):
                        continue
                    mins, det = burst_minutes(burst, caps)
                    row = TicketWorkEntry(
                        ticket_ref=s["ticket_ref"], agent_id=s["agent_id"],
                        actor_kind="tech_via_ai", actor_username=resolve(s["user"])[0],
                        actor_display=resolve(s["user"])[1], actor_user=resolve(s["user"])[2],
                        surface=s["surface"], started_at=burst[0], ended_at=burst[-1],
                        human_minutes=mins, ai_minutes=0,
                        confidence="measured", method=method_label(caps),
                        evidence={"session_id": s["session_id"], "burst": bi + 1,
                                  "of_bursts": len(bursts),
                                  "human_turns_in_burst": sum(1 for t in burst if t in user_set),
                                  **det},
                        source="backfill:transcript", note=(s["name"] or "")[:200],
                    )
                    if TicketWorkEntry.objects.filter(
                            ticket_ref=s["ticket_ref"], agent_id=s["agent_id"],
                            actor_username=s["user"], started_at=burst[0],
                            ended_at=burst[-1]).exists():
                        skipped_existing += 1
                        continue
                    if o["commit"]:
                        row.save()
                    made.append(row)
                continue
            elif tr:
                skipped_nowork += 1
                continue
            else:
                # No transcript on disk: the index still proves a person was in there, but the
                # duration is not evidenced. Recorded as ESTIMATED and never as measured.
                no_transcript += 1
                started = s["started"] or s["last_activity"]
                ended = s["last_activity"]
                span = max(0.0, (ended - started).total_seconds() / 60)
                if span < 1:
                    skipped_nowork += 1
                    continue
                mins = round(min(span, 60.0) + caps["lead_in"] + caps["tail"], 1)
                conf, method = "estimated", "index-span-only(capped60)"
                ev = {"session_id": s["session_id"], "why": "transcript not on disk",
                      "index_span_min": round(span, 1)}

            row = TicketWorkEntry(
                ticket_ref=s["ticket_ref"], agent_id=s["agent_id"],
                actor_kind="tech_via_ai", actor_username=resolve(s["user"])[0],
                actor_display=resolve(s["user"])[1], actor_user=resolve(s["user"])[2],
                surface=s["surface"], started_at=started, ended_at=ended,
                human_minutes=mins, ai_minutes=0,
                confidence=conf, method=method, evidence=ev,
                source=f"backfill:{'transcript' if conf == 'measured' else 'index'}",
                note=(s["name"] or "")[:200],
            )
            if o["commit"]:
                row.save()
            made.append(row)

        if o["commit"]:
            overlapped = mark_overlaps([r for r in made if r.id])
        else:
            overlapped = 0

        verb = "wrote" if o["commit"] else "would write"
        self.stdout.write(self.style.SUCCESS(
            f"{len(sessions)} sessions in {o['days']}d | {verb} {len(made)} entries "
            f"(measured {sum(1 for r in made if r.confidence == 'measured')}, "
            f"estimated {sum(1 for r in made if r.confidence == 'estimated')}) | "
            f"skipped: {skipped_existing} already present, {skipped_nowork} no real work | "
            f"overlaps marked: {overlapped}"))

        if not o["quiet_rows"]:
            tot = {}
            for r in made:
                tot[r.actor_display] = tot.get(r.actor_display, 0) + (r.human_minutes or 0)
            for who, m in sorted(tot.items(), key=lambda x: -x[1]):
                self.stdout.write(f"   {who:20} {m/60:6.1f} h  ({m:.0f} min)")
