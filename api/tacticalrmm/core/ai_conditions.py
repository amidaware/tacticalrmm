"""The condition engine: one evaluator, no vendor knowledge.

WHAT THIS REPLACES. Recognising a machine notification used to mean adding a hand-written
rule to a JS code box - one bespoke function per product, extendable only by a developer,
growing forever, and invisible to the people who actually know the fleet. Vendor knowledge
belongs in procedures: rows a technician can read, edit and approve, that the miner can
propose, and that carry their own fix and verification text.

WHAT IT DOES. For an incoming ticket it asks: does an APPROVED, auto-enabled procedure
declare how to recognise this? If one does, its `disposition` is the ruling - deterministic,
no model call, same answer every time. If the procedure also carries a `condition_key`, the
recurrence ledger decides whether this is the first time (tell the customer, once) or a
repeat of something already tracked (suppress it against the tracker).

WHAT IT DELIBERATELY IS NOT. `match` is declarative: patterns and required phrases. Never an
expression to evaluate. A procedure whose matching logic cannot be read by the person
approving it is not reviewable, and we would have rebuilt the code box with extra steps.

MANDATE notes: the ruling is code (§4.8) driven by human-approved data; nothing here writes
to a customer, and suppression always leaves a tracker open and a note behind (§4.9).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# A pattern from a data row is still a pattern: cap it, compile it defensively, and let a
# bad row disable itself rather than take the poller down.
MAX_PATTERN = 400
MAX_PHRASES = 25


def _rx(pattern: str) -> Optional[re.Pattern]:
    if not pattern or len(pattern) > MAX_PATTERN:
        return None
    try:
        return re.compile(pattern, re.I | re.M)
    except re.error:
        return None


def _phrases(v: Any) -> List[str]:
    if isinstance(v, str):
        v = [v]
    if not isinstance(v, list):
        return []
    return [str(x) for x in v[:MAX_PHRASES] if str(x).strip()]


def evaluate_match(spec: Dict[str, Any], *, subject: str, body: str, sender: str) -> Tuple[bool, Dict[str, str]]:
    """Declarative recognition. Returns (matched, extracted identity fields).

    Every declared test must pass. An empty spec never matches - a procedure has to say
    what it recognises before it is allowed to rule on anything.
    """
    if not isinstance(spec, dict) or not spec:
        return False, {}

    subject = subject or ""
    body = body or ""
    sender = sender or ""
    hay = f"{subject}\n{body}"

    sr = spec.get("subject_regex")
    if sr:
        rx = _rx(str(sr))
        if not rx or not rx.search(subject):
            return False, {}

    br = spec.get("body_regex")
    if br:
        rx = _rx(str(br))
        if not rx or not rx.search(body):
            return False, {}

    sender_rx = spec.get("sender_regex")
    if sender_rx:
        rx = _rx(str(sender_rx))
        if not rx or not rx.search(sender):
            return False, {}

    for phrase in _phrases(spec.get("body_all")):
        if phrase.lower() not in hay.lower():
            return False, {}

    any_phrases = _phrases(spec.get("body_any"))
    if any_phrases and not any(p.lower() in hay.lower() for p in any_phrases):
        return False, {}

    for phrase in _phrases(spec.get("body_none")):
        if phrase.lower() in hay.lower():
            return False, {}

    # Identity extraction: which box, and (optionally) which customer the text names.
    ident: Dict[str, str] = {}
    idspec = spec.get("identity") if isinstance(spec.get("identity"), dict) else {}
    for out_key, in_key in (("host", "host_regex"), ("customer", "customer_regex")):
        pat = idspec.get(in_key)
        if not pat:
            continue
        rx = _rx(str(pat))
        if not rx:
            continue
        m = rx.search(hay)
        if m:
            ident[out_key] = (m.group(1) if m.groups() else m.group(0)).strip()[:200]
    return True, ident


def find_condition(*, subject: str, body: str, sender: str) -> Optional[Dict[str, Any]]:
    """The first live procedure that recognises this ticket, with its identity fields.

    Ordered by occurrence_count so the best-evidenced procedure wins a tie. Only
    `is_live_rule` rows are considered: approved, auto-enabled, and carrying both a
    condition key and a disposition.
    """
    from core.models import AIProcedure

    rows = AIProcedure.objects.filter(
        status="approved", auto_enabled=True,
    ).exclude(condition_key="").exclude(disposition="").order_by("-occurrence_count", "id")

    for p in rows:
        if not p.is_live_rule:
            continue
        ok, ident = evaluate_match(p.match, subject=subject, body=body, sender=sender)
        if not ok:
            continue
        return {
            "procedure": p,
            "condition_key": p.condition_key,
            "disposition": p.disposition,
            "evidence": p.evidence,
            "identity": ident,
            "repeat_policy": p.repeat_policy if isinstance(p.repeat_policy, dict) else {},
            "fix": p.fix,
            "verification": p.verification,
            "title": p.title,
        }
    return None


def record_occurrence(hit: Dict[str, Any], *, ticket_ref: str, customer_key: str,
                      host: str = "") -> Dict[str, Any]:
    """Advance the recurrence ledger for a matched condition.

    Returns the decision for THIS ticket:
      {"action": "track",    "row": …}  - first sighting; this ticket becomes the tracker
      {"action": "suppress", "row": …}  - a repeat of something already tracked
      {"action": "open",     "row": …}  - tracked, but suppression is not authorised
    Nothing here talks to the helpdesk; the caller owns that, so this stays testable.
    """
    from django.utils import timezone as djangotime

    from core.models import AIKnownCondition

    pol = hit.get("repeat_policy") or {}
    row, created = AIKnownCondition.objects.get_or_create(
        condition_key=hit["condition_key"],
        customer_key=(customer_key or "")[:200],
        host=(host or "")[:200],
        defaults={
            "procedure": hit.get("procedure"),
            "tracker_ref": ticket_ref,
            "state": "advising",
            "last_ticket_ref": ticket_ref,
            "detail": hit.get("title", "")[:2000],
        },
    )
    if created:
        return {"action": "track", "row": row, "first": True}

    row.occurrences = (row.occurrences or 0) + 1
    row.last_ticket_ref = ticket_ref
    if not row.tracker_ref:
        row.tracker_ref = ticket_ref
    if row.procedure_id is None and hit.get("procedure"):
        row.procedure = hit["procedure"]

    # A human who muted this condition outranks the policy.
    if row.state == "muted":
        row.save(update_fields=["occurrences", "last_ticket_ref", "tracker_ref", "procedure", "last_seen"])
        return {"action": "open", "row": row, "reason": "condition muted by a human"}

    # It came back after we thought it had stopped: reopen the tracking, do not suppress
    # silently - something changed.
    if row.state == "resolved":
        row.state = "advising"
        row.tracker_ref = ticket_ref
        row.save(update_fields=["occurrences", "last_ticket_ref", "tracker_ref", "procedure",
                                "state", "last_seen"])
        return {"action": "track", "row": row, "reason": "recurred after being resolved"}

    if row.tracker_ref == ticket_ref:
        row.save(update_fields=["occurrences", "last_ticket_ref", "procedure", "last_seen"])
        return {"action": "open", "row": row, "reason": "this IS the tracker"}

    if not pol.get("suppress_repeats"):
        row.save(update_fields=["occurrences", "last_ticket_ref", "tracker_ref", "procedure", "last_seen"])
        return {"action": "open", "row": row, "reason": "procedure does not authorise suppression"}

    row.suppressed = (row.suppressed or 0) + 1
    row.save(update_fields=["occurrences", "suppressed", "last_ticket_ref", "tracker_ref",
                            "procedure", "last_seen"])
    return {"action": "suppress", "row": row}


def mute_if_tracker_gone(row, *, tracker_stage: str, by: str = "") -> bool:
    """A human closing the tracker is an instruction, not an accident.

    If someone cancels or closes the tracker, they have decided they do not want tickets
    about this condition. Continuing to suppress duplicates "against" a dead ticket would
    bury the finding behind a link that goes nowhere - the exact failure this ledger exists
    to prevent. So the condition is marked MUTED instead: repeats stay suppressed (their
    wish), the count keeps rising (the evidence), and the finding is still on the books to
    be surfaced in a review rather than as another ticket.

    Returns True if it just muted the row.
    """
    if not tracker_stage:
        return False
    terminal = any(w in tracker_stage.lower() for w in ("clos", "cancel", "done", "billing"))
    if not terminal or row.state == "muted":
        return False
    row.state = "muted"
    row.detail = (
        (row.detail or "") +
        f"\n\nMUTED: the tracker {row.tracker_ref} was moved to '{tracker_stage}'"
        + (f" by {by}" if by else "") +
        ". Treating that as a decision not to hold a ticket open for this condition. "
        "Repeats stay suppressed and keep being counted, but no new ticket is raised. "
        "The condition itself is unchanged - it needs surfacing in a review, not a ticket."
    ).strip()[:4000]
    row.save(update_fields=["state", "detail"])
    return True


def mark_advised(row, ticket_ref: str = "") -> None:
    """Called once a human/AI has actually told the customer, so repeats can be suppressed."""
    from django.utils import timezone as djangotime

    if row.state == "advising":
        row.state = "advised"
        row.advised_at = djangotime.now()
        if ticket_ref:
            row.tracker_ref = ticket_ref
        row.save(update_fields=["state", "advised_at", "tracker_ref"])
