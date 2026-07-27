"""Build the work ledger from evidence: chat transcripts, and helpdesk message bursts.

THE MEASUREMENT. A chat transcript carries a timestamp per turn, so attention time is derived
rather than guessed: walk consecutive events, add the real gap, and when a gap is longer than
the idle cap treat it as "walked away" and credit only the re-orientation cost. Add a lead-in
(reading before typing) and a tail (reading the final answer). The rule is recorded on every
row as `method`, so any number here can be recomputed and argued with.

WHAT COUNTS AS WORK. Opening a window is not work. A session earns a row when a human actually
did something: at least one typed turn AND either a tool call or enough elapsed time to have
read something. Everything else is noise and would inflate the ledger.

PARALLEL WORK COUNTS IN FULL (owner's ruling). Overlapping sessions are recorded with their
overlap so it is visible, and never reduced: three windows for fifteen minutes is forty-five
minutes of work.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

SESSION_ROOT = "/opt/pi-trmm-bridge/sessions"
TICKET_ROOT = os.path.join(SESSION_ROOT, "decision:TICKET")


def _norm(ts) -> Optional[datetime]:
    if ts is None:
        return None
    try:
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts / 1000 if ts > 1e11 else ts, tz=timezone.utc)
        t = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def read_transcript(path: str) -> Dict[str, Any]:
    """Timestamps and shape of one session: every event, the human turns, the tool calls."""
    events: List[datetime] = []
    user_turns: List[datetime] = []
    assistant_turns = 0
    tool_calls = 0
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r", errors="replace") as fh:
            for line in fh:
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                m = d.get("message") or {}
                t = _norm(m.get("timestamp") or d.get("timestamp"))
                if not t:
                    continue
                events.append(t)
                role = m.get("role")
                if role == "user":
                    user_turns.append(t)
                elif role == "assistant":
                    assistant_turns += 1
                    for c in (m.get("content") or []):
                        if isinstance(c, dict) and c.get("type") == "toolCall":
                            tool_calls += 1
    except Exception:
        return {}
    if not events:
        return {}
    events.sort()
    return {
        "events": events, "user_turns": user_turns, "n_events": len(events),
        "n_user_turns": len(user_turns), "n_assistant": assistant_turns,
        "n_tool_calls": tool_calls, "start": events[0], "end": events[-1],
    }


def attention_minutes(events: List[datetime], caps: Dict[str, int]) -> Tuple[float, Dict[str, Any]]:
    """Gap-capped attention time. Returns (minutes, how-it-was-derived)."""
    idle = caps["idle_cap"]
    away = caps["away_credit"]
    lead = caps["lead_in"]
    tail = caps["tail"]
    if not events:
        return 0.0, {"capped_gaps": 0, "raw_span_min": 0}
    if len(events) == 1:
        return float(lead + tail), {"capped_gaps": 0, "raw_span_min": 0}
    total, capped, longest = 0.0, 0, 0.0
    for a, b in zip(events, events[1:]):
        gap = (b - a).total_seconds() / 60
        longest = max(longest, gap)
        if gap > idle:
            total += away
            capped += 1
        else:
            total += gap
    span = (events[-1] - events[0]).total_seconds() / 60
    return round(total + lead + tail, 1), {
        "capped_gaps": capped, "raw_span_min": round(span, 1),
        "longest_gap_min": round(longest, 1),
    }


def split_bursts(events: List[datetime], idle_cap: int) -> List[List[datetime]]:
    """Cut a transcript into separate WORK SESSIONS at every long gap.

    A transcript persists for the life of a ticket or device, so one file can span days: open
    it Monday, resume it Thursday. Treating that as a single entry produced rows with a
    six-day span, which cannot be attributed to a day and made overlap detection meaningless
    (every long row "overlapped" everything). A gap longer than the idle cap is not a pause in
    a session, it is the end of one - so it ends the entry and the next event starts a new one.
    """
    if not events:
        return []
    bursts, cur = [], [events[0]]
    for a, b in zip(events, events[1:]):
        if (b - a).total_seconds() / 60 > idle_cap:
            bursts.append(cur)
            cur = [b]
        else:
            cur.append(b)
    bursts.append(cur)
    return bursts


def burst_minutes(burst: List[datetime], caps: Dict[str, int]) -> Tuple[float, Dict[str, Any]]:
    """Time for one burst: its real span, plus reading in and reading out.

    No gap-capping needed inside a burst - by construction every gap is under the cap. Each
    return to the work pays its own lead-in and tail, which is the honest cost of picking a
    thread back up.
    """
    span = (burst[-1] - burst[0]).total_seconds() / 60 if len(burst) > 1 else 0.0
    return round(span + caps["lead_in"] + caps["tail"], 1), {
        "raw_span_min": round(span, 1), "events_in_burst": len(burst),
    }


def caps_from_settings(core) -> Dict[str, int]:
    return {
        "compose_cpm": int(getattr(core, "ai_work_compose_chars_per_min", 200) or 200),
        "read_cpm": int(getattr(core, "ai_work_read_chars_per_min", 900) or 900),
        "idle_cap": int(getattr(core, "ai_work_idle_cap_minutes", 15) or 15),
        "away_credit": int(getattr(core, "ai_work_away_credit_minutes", 2) or 2),
        "lead_in": int(getattr(core, "ai_work_lead_in_minutes", 2) or 2),
        "tail": int(getattr(core, "ai_work_tail_minutes", 2) or 2),
    }


def method_label(caps: Dict[str, int], kind: str = "transcript-burst") -> str:
    return f"{kind}-split{caps['idle_cap']}/lead{caps['lead_in']}/tail{caps['tail']}"


def is_real_work(tr: Dict[str, Any], min_minutes: float = 1.0) -> bool:
    """Opening a chat is not work; typing at it is."""
    if not tr or not tr.get("n_user_turns"):
        return False
    span = (tr["end"] - tr["start"]).total_seconds() / 60
    return bool(tr.get("n_tool_calls") or tr.get("n_assistant") or span >= min_minutes)


def iter_sessions(days: int = 14) -> List[Dict[str, Any]]:
    """Every interactive session in the window, ticket-bound and device-only alike."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    out: List[Dict[str, Any]] = []

    def scan(base: str, ticket_mode: bool):
        if not os.path.isdir(base):
            return
        for name in sorted(os.listdir(base)):
            idx_path = os.path.join(base, name, "index.json")
            if not os.path.exists(idx_path):
                continue
            try:
                idx = json.load(open(idx_path))
            except Exception:
                continue
            for sid, v in idx.items():
                last = _norm(v.get("last_activity")) or _norm(v.get("started"))
                if not last or last < cutoff:
                    continue
                out.append({
                    "session_id": sid,
                    "user": (v.get("user") or "").strip(),
                    "file": v.get("file") or "",
                    "started": _norm(v.get("started")),
                    "last_activity": last,
                    "model": v.get("model") or "",
                    "name": v.get("name") or "",
                    "ticket_ref": f"TICKET/{name}" if ticket_mode else "",
                    "agent_id": "" if ticket_mode else name,
                    "surface": "ticket_chat" if ticket_mode else "device_chat",
                    "multi": bool(v.get("multi")),
                })

    scan(TICKET_ROOT, True)
    # Device chats live directly under the sessions root, one directory per agent id.
    for name in sorted(os.listdir(SESSION_ROOT)):
        if name.startswith("decision:"):
            continue
        idx_path = os.path.join(SESSION_ROOT, name, "index.json")
        if not os.path.exists(idx_path):
            continue
        try:
            idx = json.load(open(idx_path))
        except Exception:
            continue
        for sid, v in idx.items():
            last = _norm(v.get("last_activity")) or _norm(v.get("started"))
            if not last or last < cutoff:
                continue
            out.append({
                "session_id": sid, "user": (v.get("user") or "").strip(),
                "file": v.get("file") or "", "started": _norm(v.get("started")),
                "last_activity": last, "model": v.get("model") or "", "name": v.get("name") or "",
                "ticket_ref": "", "agent_id": name, "surface": "device_chat",
                "multi": bool(v.get("multi")),
            })
    return out


def mark_overlaps(entries) -> int:
    """Record which entries overlapped in time, per person. Never deducts - see the model."""
    from collections import defaultdict

    by_user = defaultdict(list)
    for e in entries:
        if e.actor_username:
            by_user[e.actor_username].append(e)
    touched = 0
    for _user, rows in by_user.items():
        rows.sort(key=lambda r: r.started_at)
        for i, a in enumerate(rows):
            ids, mins = [], 0.0
            for b in rows[i + 1:]:
                if b.started_at >= a.ended_at:
                    break
                overlap = (min(a.ended_at, b.ended_at) - b.started_at).total_seconds() / 60
                if overlap > 0.5:
                    ids.append(b.id)
                    mins += overlap
            if ids:
                a.overlaps_ids = ids
                a.overlap_minutes = round(mins, 1)
                a.note = (a.note + " " if a.note else "") + f"parallel with {len(ids)} other session(s)"
                a.save(update_fields=["overlaps_ids", "overlap_minutes", "note"])
                touched += 1
    return touched


def apply_baseline(entry, procedures_matcher=None) -> None:
    """Attach a time-saved estimate IF a human has authored a baseline for this class of work.

    Deliberately silent when no baseline exists: inventing "what it would have taken" is how
    the old 'saved by AI' number lost its credibility.
    """
    from core.ai_match import match_procedures

    if entry.human_minutes is None:
        return
    hits = match_procedures(entry.ticket_ref or "", entry.note or "", limit=3)
    for h in hits:
        from core.models import AIProcedure
        p = AIProcedure.objects.filter(id=h["id"]).only("baseline_minutes", "title").first()
        if p and p.baseline_minutes:
            entry.baseline_minutes = p.baseline_minutes
            entry.baseline_source = f"procedure #{p.id}: {p.title[:120]}"
            entry.saved_minutes = round(max(0.0, p.baseline_minutes - (entry.human_minutes or 0)), 1)
            entry.save(update_fields=["baseline_minutes", "baseline_source", "saved_minutes"])
            return


# ---------------------------------------------------------------------------
# TECH-DIRECT WORK: someone worked the ticket by hand, in the helpdesk.
#
# There IS evidence, it is just weaker than a transcript: the messages they wrote and when.
# Group a person's messages on one ticket into bursts and the shape of the work appears - a
# single reply is a few minutes; four notes over half an hour is half an hour. Labelled
# `sessionized`, never `measured`, because the gaps between messages are inferred, not observed.

def sessionize_staff_events(events: List[Dict[str, Any]], caps: Dict[str, int]
                            ) -> Dict[str, List[Dict[str, Any]]]:
    """{actor: [burst, ...]} where a burst carries its timing AND its content volume.

    Timestamps alone say a technician who posted three considered replies inside one minute did
    zero seconds of work. Content says otherwise: those replies had to be composed, and the
    thread before them had to be read. Both are recorded here so the caller can take whichever
    estimate is larger, and say which one it used.
    """
    ordered = []
    for e in events:
        t = _norm(e.get("at"))
        if t:
            ordered.append((t, e))
    ordered.sort(key=lambda x: x[0])

    by_actor: Dict[str, List[Tuple[datetime, int]]] = {}
    for t, e in ordered:
        if e.get("kind") == "staff":
            by_actor.setdefault(str(e.get("actor") or "?"), []).append((t, int(e.get("chars") or 0)))

    out: Dict[str, List[Dict[str, Any]]] = {}
    for actor, items in by_actor.items():
        items.sort(key=lambda x: x[0])
        stamps = [t for t, _c in items]
        chars_at = {t: c for t, c in items}
        prev_end = None
        for burst in split_bursts(stamps, caps["idle_cap"]):
            own_chars = sum(chars_at.get(t, 0) for t in burst)
            # Everything the OTHER side wrote since this actor last spoke: the reading that had
            # to happen before this reply could be written.
            inbound = 0
            for t, e in ordered:
                if e.get("kind") == "staff" and str(e.get("actor") or "?") == actor:
                    continue
                if t <= burst[-1] and (prev_end is None or t > prev_end):
                    inbound += int(e.get("chars") or 0)
            out.setdefault(actor, []).append({
                "start": burst[0], "end": burst[-1], "messages": len(burst),
                "own_chars": own_chars, "inbound_chars": inbound,
            })
            prev_end = burst[-1]
    return out


def work_minutes_for_burst(b: Dict[str, Any], caps: Dict[str, int]) -> Tuple[float, str, Dict[str, Any]]:
    """The larger of "how long it lasted" and "how much was written and read"."""
    span = (b["end"] - b["start"]).total_seconds() / 60
    by_span = span + caps["lead_in"] + caps["tail"]
    compose = b["own_chars"] / max(1, caps["compose_cpm"])
    reading = b["inbound_chars"] / max(1, caps["read_cpm"])
    by_content = compose + reading + caps["lead_in"] + caps["tail"]
    if by_content > by_span:
        return (round(by_content, 1), "content",
                {"raw_span_min": round(span, 1), "compose_min": round(compose, 1),
                 "read_min": round(reading, 1), "own_chars": b["own_chars"],
                 "inbound_chars": b["inbound_chars"], "messages_in_burst": b["messages"]})
    return (round(by_span, 1), "span",
            {"raw_span_min": round(span, 1), "compose_min": round(compose, 1),
             "read_min": round(reading, 1), "own_chars": b["own_chars"],
             "inbound_chars": b["inbound_chars"], "messages_in_burst": b["messages"]})


def actor_index() -> Tuple[Dict[str, Tuple[str, str]], Dict[str, str]]:
    """(name -> (username, display)), plus the alias map.

    Two traps this closes. A person can have MORE THAN ONE account with the same display name
    (a personal login and a shared support login), so a plain name lookup assigns their work to
    whichever record happens to iterate first. And a RENAME forks history unless old labels are
    mapped forward. So: prefer an active account whose username is not an email address - a real
    login over a shared mailbox login - and consult an explicit alias map.
    """
    from accounts.models import User

    from core.models import CoreSettings

    core = CoreSettings.objects.first()
    aliases = {str(k).lower(): str(v) for k, v in
               (getattr(core, "ai_work_actor_aliases", None) or {}).items()}
    by_name: Dict[str, Tuple[str, str]] = {}
    for u in User.objects.filter(is_active=True):
        full = (u.get_full_name() or "").strip()
        if not full:
            continue
        key = full.lower()
        better = ("@" not in u.username)
        if key not in by_name or (better and "@" in by_name[key][0]):
            by_name[key] = (u.username, full)
    return by_name, aliases


def resolve_user(raw: str):
    """The User record behind a username or a helpdesk display label - the identity that lasts."""
    from accounts.models import User

    by_name, aliases = actor_index()
    uname, _disp = canonical_actor(raw, by_name, aliases)
    return User.objects.filter(username=uname).first() if uname else None


def canonical_actor(raw: str, by_name: Dict[str, Tuple[str, str]], aliases: Dict[str, str]
                    ) -> Tuple[str, str]:
    """Resolve a username OR a helpdesk display label to (canonical username, display name)."""
    from accounts.models import User

    clean = str(raw or "").replace("BlueCloud IAAS, LLC,", "").strip()
    if not clean:
        return "", ""
    target = aliases.get(clean.lower(), clean)
    hit = by_name.get(str(target).lower())
    if hit:
        return hit
    u = User.objects.filter(username=target).first()
    if u:
        return u.username, (u.get_full_name() or u.username)
    return "", clean


def helpdesk_name_to_user(display: str, user_map: Dict[str, str]) -> Tuple[str, str]:
    """Back-compat shim: resolve a helpdesk actor label to (username, display)."""
    by_name, aliases = actor_index()
    return canonical_actor(display, by_name, aliases)


def refresh_from_helpdesk(hours: int = 48, commit: bool = True) -> Dict[str, Any]:
    """Bring the ledger up to date with hand-worked tickets. Safe to call repeatedly.

    Called before any summary email is generated, so a report never reads a stale ledger -
    which was the whole problem with the old estimate: it was computed at send time from
    whatever heuristic happened to be in the formatter.
    """
    import requests as _requests
    from django.conf import settings as dj_settings

    from accounts.models import User

    from core.models import CoreSettings, TicketWorkEntry

    core = CoreSettings.objects.first()
    if not core or not (core.ai_helpdesk_code or "").strip():
        return {"ok": False, "error": "no helpdesk integration"}
    caps = caps_from_settings(core)
    bridge = getattr(dj_settings, "PI_BRIDGE_URL", "http://127.0.0.1:8787")
    try:
        r = _requests.post(f"{bridge}/pi/helpdesk-op", json={
            "operation": "ticket_message_events",
            "args": {"hours": hours, "all_teams": True},
            "helpdesk_api": {"base_url": core.ai_helpdesk_api_base_url or "",
                             "api_key": core.ai_helpdesk_api_key or ""},
            "helpdesk_code": core.ai_helpdesk_code or "",
        }, timeout=(10, 600)).json()
    except Exception as e:
        return {"ok": False, "error": f"helpdesk call failed: {e}"}
    rows = r.get("result")
    if not isinstance(rows, list):
        return {"ok": False, "error": str(r.get("error"))[:300]}

    user_map = {u.username: (u.get_full_name() or u.username) for u in User.objects.all()}
    staff = set(staff_users())
    made, seen = 0, 0
    for t in rows:
        ref = t.get("ref")
        if not ref:
            continue
        for actor, bursts in sessionize_staff_events(t.get("events") or [], caps).items():
            uname, disp = helpdesk_name_to_user(actor, user_map)
            if uname and uname not in staff:
                continue     # a customer contact writing on their own ticket is not our work
            for b in bursts:
                seen += 1
                mins, basis, det = work_minutes_for_burst(b, caps)
                method = (f"msgburst-{basis}-split{caps['idle_cap']}/lead{caps['lead_in']}"
                          f"/tail{caps['tail']}/cpm{caps['compose_cpm']}")
                existing = TicketWorkEntry.objects.filter(
                    ticket_ref=ref, actor_display=disp, surface="helpdesk_direct",
                    started_at=b["start"], superseded_by=None).first()
                if existing:
                    if abs((existing.human_minutes or 0) - mins) < 0.2:
                        continue
                    if not commit:
                        made += 1
                        continue
                    # The estimate improved. Corrections are new rows, never edits, so an
                    # already-sent report can still be reproduced exactly.
                    new = TicketWorkEntry.objects.create(
                        ticket_ref=ref, actor_kind="tech", actor_username=uname,
                        actor_user=User.objects.filter(username=uname).first() if uname else None,
                        actor_display=disp, surface="helpdesk_direct",
                        started_at=b["start"], ended_at=b["end"], human_minutes=mins, ai_minutes=0,
                        confidence="sessionized", method=method,
                        evidence={**det, "subject": (t.get("subject") or "")[:120],
                                  "supersedes": existing.id},
                        source="backfill:messages",
                        note=f"revised from {existing.human_minutes}m ({basis} basis)"[:400],
                    )
                    existing.superseded_by = new
                    existing.save(update_fields=["superseded_by"])
                    made += 1
                    continue
                if commit:
                    TicketWorkEntry.objects.create(
                        ticket_ref=ref, actor_kind="tech", actor_username=uname,
                        actor_user=User.objects.filter(username=uname).first() if uname else None,
                        actor_display=disp, surface="helpdesk_direct",
                        started_at=b["start"], ended_at=b["end"], human_minutes=mins, ai_minutes=0,
                        confidence="sessionized", method=method,
                        evidence={**det, "subject": (t.get("subject") or "")[:120]},
                        source="backfill:messages", note=(t.get("subject") or "")[:200],
                    )
                made += 1
    return {"ok": True, "tickets": len(rows), "bursts_seen": seen, "entries_added": made}


# ---------------------------------------------------------------------------
# RMM ACTIVITY: the work that happens on devices, not in tickets.
#
# The third source, and the one whose absence made a technician's day look empty. A tech
# spends the afternoon in remote sessions on a machine, adds a network device, runs a script -
# none of that writes a helpdesk message or an AI transcript, so both earlier sources saw
# nothing. The RMM audit log sees all of it, with a timestamp per action, which sessionizes the
# same way everything else does.
#
# Not ticket-linked on purpose: RMM actions do not carry a ticket reference, and guessing one
# from "a device that appears in some ticket" would invent attribution. It counts as time
# worked; it just does not claim to know which ticket paid for it.

SERVICE_ACCOUNTS = {"BlueCloud-ai", "pi-bridge-service", "BlueCloud-API", "system", "OdooBot"}


def staff_domains(core=None) -> List[str]:
    """Which email domains are OURS. Defaults to the domain we send mail from."""
    from core.models import CoreSettings

    core = core or CoreSettings.objects.first()
    doms = [str(d).strip().lower().lstrip("@") for d in
            (getattr(core, "ai_staff_email_domains", None) or []) if str(d).strip()]
    if doms:
        return doms
    frm = (getattr(core, "smtp_from_email", "") or "")
    return [frm.split("@")[-1].strip().lower()] if "@" in frm else []


def is_staff_user(u, doms: Optional[List[str]] = None, extras: Optional[set] = None) -> bool:
    """Do they work HERE? A customer with a portal login is a named human but not a colleague.

    Deliberately not role-based: role names are a naming convention and a new client role would
    silently qualify. The mail domain is the fact.
    """
    from core.models import CoreSettings

    if not u or not u.is_active or u.username in SERVICE_ACCOUNTS:
        return False
    if extras is None:
        core = CoreSettings.objects.first()
        extras = {str(x).strip().lower() for x in
                  (getattr(core, "ai_staff_extra_usernames", None) or [])}
    if u.username.lower() in extras:
        return True
    if doms is None:
        doms = staff_domains()
    if not doms:
        return True          # nothing configured and no send domain: do not silently exclude
    for field in (u.email or "", u.username or ""):
        if "@" in field and field.split("@")[-1].strip().lower() in doms:
            return True
    return False


def staff_users() -> Dict[str, Any]:
    """{username: User} for everyone who works here."""
    from accounts.models import User

    from core.models import CoreSettings

    core = CoreSettings.objects.first()
    doms = staff_domains(core)
    extras = {str(x).strip().lower() for x in (getattr(core, "ai_staff_extra_usernames", None) or [])}
    return {u.username: u for u in User.objects.filter(is_active=True)
            if is_staff_user(u, doms, extras)}


def refresh_from_rmm_audit(hours: int = 168, commit: bool = True) -> Dict[str, Any]:
    from datetime import timedelta

    from django.utils import timezone as djangotime

    from accounts.models import User
    from logs.models import AuditLog

    from core.models import CoreSettings, TicketWorkEntry

    core = CoreSettings.objects.first()
    caps = caps_from_settings(core)
    since = djangotime.now() - timedelta(hours=max(1, int(hours or 168)))
    by_name, aliases = actor_index()

    # Only real people: a service account or an agent token is not someone's working day.
    # Staff only: a client admin using their own portal is not our technician's day.
    humans = {uname: (u.get_full_name() or uname) for uname, u in staff_users().items()
              if (u.get_full_name() or "").strip()}
    # History does not rename itself: audit rows written before a username change still carry
    # the old name, so every alias that points at a real person must be queried too - otherwise
    # that person's pre-rename work silently disappears.
    for old, new in aliases.items():
        if new in humans and old not in humans:
            humans[old] = humans[new]

    rows = (AuditLog.objects.filter(entry_time__gte=since, username__in=list(humans))
            .only("username", "entry_time", "action", "object_type", "message")
            .order_by("username", "entry_time"))
    per_user: Dict[str, List[Any]] = {}
    for a in rows:
        per_user.setdefault(a.username, []).append(a)

    added, bursts_seen = 0, 0
    for uname, entries in per_user.items():
        stamps = [a.entry_time for a in entries]
        for burst in split_bursts(stamps, caps["idle_cap"]):
            bursts_seen += 1
            start, end = burst[0], burst[-1]
            acts = [a for a in entries if start <= a.entry_time <= end]
            kinds: Dict[str, int] = {}
            for a in acts:
                kinds[a.action] = kinds.get(a.action, 0) + 1
            # A lone login is not work - it is the door opening.
            if len(acts) <= 1 and set(kinds) <= {"login"}:
                continue
            mins, det = burst_minutes(burst, caps)
            canon_user, canon_disp = canonical_actor(uname, by_name, aliases)
            if TicketWorkEntry.objects.filter(actor_username=canon_user or uname,
                                              surface="rmm_activity",
                                              started_at=start).exists():
                continue
            if commit:
                TicketWorkEntry.objects.create(
                    ticket_ref="", agent_id="",
                    actor_kind="tech", actor_username=canon_user or uname,
                    actor_user=User.objects.filter(username=canon_user or uname).first(),
                    actor_display=canon_disp or humans.get(uname, uname),
                    surface="rmm_activity", started_at=start, ended_at=end,
                    human_minutes=mins, ai_minutes=0,
                    confidence="sessionized",
                    method=f"auditburst-split{caps['idle_cap']}/lead{caps['lead_in']}/tail{caps['tail']}",
                    evidence={"actions": len(acts), "action_kinds": kinds, **det},
                    source="backfill:rmm-audit",
                    note=", ".join(f"{k}x{v}" for k, v in sorted(kinds.items(), key=lambda x: -x[1])[:4])[:200],
                )
            added += 1
    return {"ok": True, "users": len(per_user), "bursts_seen": bursts_seen, "entries_added": added}


def coverage_report(hours: int = 24) -> List[Dict[str, Any]]:
    """Per person: what the ledger holds, and what raw signal exists that it could not time.

    The point is to stop a quiet day reading as a lazy one. If someone has RMM actions and
    helpdesk replies but no timeable session, the report must say "activity seen, not timed" -
    not rank them at four minutes and let a reader draw a conclusion.
    """
    from datetime import timedelta

    from django.db.models import Count, Sum
    from django.utils import timezone as djangotime

    from accounts.models import User
    from logs.models import AuditLog

    from core.models import TicketWorkEntry

    since = djangotime.now() - timedelta(hours=max(1, int(hours or 24)))
    out = []
    by_name, aliases = actor_index()
    people = {}
    for u in staff_users().values():
        full = (u.get_full_name() or "").strip()
        if not full:
            continue
        cu, cd = canonical_actor(u.username, by_name, aliases)
        people[cu or u.username] = cd or full
    led = {}
    for r in (TicketWorkEntry.objects.filter(started_at__gte=since, superseded_by=None)
              .values("actor_user_id", "actor_username").annotate(m=Sum("human_minutes"), n=Count("id"))):
        key = r["actor_user_id"] or r["actor_username"]
        cur = led.setdefault(key, {"m": 0.0, "n": 0})
        cur["m"] += r["m"] or 0
        cur["n"] += r["n"] or 0
    aud = {}
    for r in (AuditLog.objects.filter(entry_time__gte=since)
              .values("username").annotate(n=Count("id"))):
        cu, _ = canonical_actor(r["username"], by_name, aliases)
        key = cu or r["username"]
        aud[key] = aud.get(key, 0) + r["n"]
    id_of = {u.username: u.id for u in User.objects.filter(is_active=True)}
    for uname, disp in sorted(people.items(), key=lambda x: x[1]):
        l = led.get(id_of.get(uname)) or led.get(uname) or {}
        rec = {"username": uname, "display": disp,
               "ledger_minutes": round(l.get("m") or 0, 1), "ledger_entries": l.get("n") or 0,
               "rmm_actions": aud.get(uname, 0)}
        rec["state"] = ("timed" if rec["ledger_minutes"] >= 5 else
                        "activity seen, not timed" if (rec["rmm_actions"] or rec["ledger_entries"]) else
                        "no activity recorded")
        if rec["ledger_minutes"] or rec["rmm_actions"]:
            out.append(rec)
    return out
