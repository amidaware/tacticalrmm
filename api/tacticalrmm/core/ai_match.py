"""Match APPROVED AIProcedure runbooks to a ticket, deterministically.

Why this exists: procedures were write-only. Mining built 339 of them (37 approved) and
nothing ever fed one back into a run, so the "compounding knowledge asset" compounded in a
table nobody read. The consequence was visible on a live ticket: the AI re-derived a worse
answer than the runbook we already had, because it never saw it.

Deliberately keyword scoring in code, not an LLM call: matching must be cheap, repeatable
and explainable ("it matched because of these words"), and it runs on every ticket surface.
Only `approved` procedures are ever injected - a draft mined from one messy ticket has no
business steering a customer reply.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

# Words that match everything and therefore discriminate nothing.
STOP = {
    "the", "and", "for", "with", "from", "that", "this", "not", "was", "are", "has", "have",
    "you", "your", "our", "their", "there", "when", "what", "which", "into", "onto", "out",
    "any", "all", "can", "will", "would", "should", "issue", "issues", "problem", "problems",
    "ticket", "tickets", "please", "help", "need", "needs", "user", "users", "new", "old",
    "error", "errors", "warning", "warnings", "support", "request", "requested", "on", "in",
    "at", "to", "of", "a", "an", "is", "it", "be", "by", "or", "as", "no", "yes", "we", "us",
}

WORD = re.compile(r"[a-z0-9_.-]{3,}")


def _tokens(text: str) -> set[str]:
    return {w for w in WORD.findall((text or "").lower()) if w not in STOP}


def match_procedures(*texts: str, limit: int = 3, min_score: int = 5) -> List[Dict[str, Any]]:
    """Return up to `limit` approved procedures relevant to the given text.

    Scoring: a hit in `applies_to` (the curated keyword field) counts double, since that
    field exists precisely to say "this is when I apply". Title and category hits count
    once. Ties break on occurrence_count - how often the procedure has actually been seen.

    `min_score` is 5, i.e. roughly two curated keyword hits. A threshold of 2 (one shared
    word) injected a Proxmox backup runbook into a Veeam ticket during testing: a weak match
    is worse than no match, because it steers the model with something that does not apply.
    """
    from core.models import AIProcedure

    want = set()
    for t in texts:
        want |= _tokens(t)
    if not want:
        return []

    blob = " ".join(t or "" for t in texts).lower()

    scored = []
    for p in AIProcedure.objects.filter(status="approved").only(
        "id", "title", "category", "applies_to", "symptom", "root_cause", "fix",
        "verification", "occurrence_count",
    ):
        # `applies_to` is a COMMA-separated list of keywords AND PHRASES. Splitting it into
        # bare words destroys the phrases: "configuration backup" then matches any ticket
        # containing "backup", which is how a "server backup and decommission" project
        # ticket scored a hit on a Veeam config-backup runbook. So a multi-word entry must
        # appear as that phrase, and is worth more than a single word precisely because it
        # is specific.
        entries = [e.strip().lower() for e in (p.applies_to or "").split(",") if e.strip()]
        score = 0
        for e in entries:
            if " " in e:
                if e in blob:
                    score += 3
            elif e in want:
                score += 2
        score += len(want & (_tokens(p.title) | _tokens(p.category)))
        if score >= min_score:
            scored.append((score, p.occurrence_count, p))

    scored.sort(key=lambda r: (-r[0], -r[1]))
    out = []
    for score, _occ, p in scored[:limit]:
        out.append({
            "id": p.id,
            "title": p.title,
            "category": p.category,
            "symptom": p.symptom,
            "root_cause": p.root_cause,
            "fix": p.fix,
            "verification": p.verification,
            "occurrences": p.occurrence_count,
            "score": score,
        })
    return out
