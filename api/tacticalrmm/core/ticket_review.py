"""The daily open-ticket review: what could be taken off the board today.

Different question from the activity brief. That one answers "what happened yesterday".
This one answers "what is sitting there, and which of it could the AI actually finish" -
so the reader can assign or click straight into the work.

DIVISION OF LABOUR, on purpose:
  * CODE gathers the facts that must not be guessed: does this customer resolve to an RMM
    client, how many of their agents are reachable, which approved procedures match, is a
    known condition recognised, how old is it, who spoke last, is anyone assigned.
  * THE MODEL buckets and phrases, grounded in those facts. Nothing in the system ACTS on
    this output - it is a report for a human - so judgement here is appropriate in a way it
    would not be for a decision that changes a ticket. If the model is unavailable, the
    deterministic fallback below still produces a usable report.
  * CODE renders and sends, and every row carries two links: the ticket, and the AI chat
    already bound to that ticket.
"""

from __future__ import annotations

import html
import json
import re
from typing import Any, Dict, List

from django.conf import settings
from django.utils.crypto import get_random_string

HUMAN_HINTS = re.compile(
    r"\b(on-?site|onsite|physically|physical|recycl|wipe[ds]?|scrap|cabling|cable run|"
    r"rack|mount|truck roll|site visit|contract|pricing|quote|invoice|negotiat|renewal|"
    r"cancel (?:services|service|account)|hardware swap|replace the (?:disk|drive|battery))\b", re.I)
THIRD_PARTY_HINTS = re.compile(
    r"\b(vendor|VAR|manufacturer|warranty|RMA|ISP|carrier|Jonas|Rightworks|CCH|"
    r"Thomson|Sage|EdgePilot|escalat\w+ to|ticket #\d+|their support)\b", re.I)
M365_HINTS = re.compile(
    r"\b(M365|Microsoft 365|Office 365|mailbox|Outlook|Exchange|distribution list|"
    r"shared mailbox|onboard\w*|offboard\w*|new (?:employee|hire|user)|password reset|MFA|"
    r"Entra|Azure AD|licen[cs]e)\b", re.I)


def gather_facts(tickets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Attach the non-negotiable facts to each open ticket. No judgement here."""
    from django.utils import timezone as djangotime

    from agents.models import Agent
    from clients.models import Client
    from core.ai_conditions import find_condition
    from core.ai_match import match_procedures
    from core.models import AIDecisionRequest, AITicketState

    clients = {c.name.lower(): c for c in Client.objects.all()}
    agents_by_client: Dict[int, List[Any]] = {}
    for a in Agent.objects.select_related("site__client").only(
        "hostname", "last_seen", "overdue_time", "offline_time", "site__client__id",
    ):
        agents_by_client.setdefault(a.site.client_id, []).append(a)

    base = (getattr(settings, "CORS_ORIGIN_WHITELIST", None) or [""])[0].rstrip("/")
    out = []
    for t in tickets:
        subj, body = t.get("subject") or "", t.get("body") or ""
        comp = (t.get("partner") or t.get("company") or "").split(",")[0].strip().lower()
        cl = clients.get(comp)
        agents = agents_by_client.get(cl.id, []) if cl else []
        online = sum(1 for a in agents if a.status == "online")
        st = AITicketState.objects.filter(ticket_ref=t["ref"]).first()
        procs = match_procedures(subj, body, limit=2)
        cond = find_condition(subject=subj, body=body, sender=t.get("requester_email", ""))

        # The durable per-ticket chat link, created if this ticket never had one, so the
        # report is clickable rather than informative.
        d = AIDecisionRequest.objects.filter(ticket_ref=t["ref"]).order_by("-updated").first()
        if not d and base:
            d = AIDecisionRequest.objects.create(
                token=get_random_string(32), ticket_ref=t["ref"], question="",
                context={"client": comp, "summary": (st.summary if st else ""),
                         "requester": (st.requester if st else t.get("requester_email", "")),
                         "classification": (st.classification if st else ""),
                         "affected_device": ""},
                messages=[], status="open",
            )
        age_days = None
        try:
            created = str(t.get("created") or "")[:10]
            if created:
                y, m, dd = [int(x) for x in created.split("-")]
                age_days = (djangotime.localtime().date() - __import__("datetime").date(y, m, dd)).days
        except Exception:
            pass

        # Who is waiting on whom, from the last speaker. A ticket where the CUSTOMER spoke
        # last is waiting on us; one where we spoke last is usually waiting on them.
        last = (t.get("recent_messages") or [{}])[0]
        last_author = str(last.get("author") or "")
        bot_or_staff = bool(t.get("last_msg_bot")) or "BlueCloud" in last_author
        # "Company, Person" is how this helpdesk files a contact; split it so the report can
        # lead with the company and name the human under it.
        _partner = (t.get("partner") or "")
        _bits = [x.strip() for x in _partner.split(",")]
        out.append({
            **t,
            "company_name": _bits[0] if _bits else "",
            "person_name": ", ".join(_bits[1:]).strip() if len(_bits) > 1 else "",
            "last_author": last_author,
            "last_date": str(last.get("date") or "")[:16],
            "waiting_on": "them" if bot_or_staff else "us",
            "age_days": age_days,
            "rmm_client": cl.name if cl else "",
            "agents": len(agents),
            "agents_online": online,
            "triage": f"{st.classification}/{st.status}" if st else "never triaged",
            "procedures": [{"title": p["title"], "score": p["score"]} for p in procs],
            "known_condition": cond["condition_key"] if cond else "",
            "chat_url": f"{base}/ai-decision/{d.token}" if (d and base) else "",
            "hint_human": bool(HUMAN_HINTS.search(f"{subj} {body}")),
            "hint_third_party": bool(THIRD_PARTY_HINTS.search(f"{subj} {body}")),
            "hint_m365": bool(M365_HINTS.search(f"{subj} {body}")),
        })
    return out


BUCKETS = [
    ("ai_now", "AI can finish now - one approval each"),
    ("ai_one_step", "AI does the work, a human does one step"),
    ("blocked_access", "Blocked only by access we do not have (e.g. M365)"),
    ("value_only", "AI adds value but cannot close it"),
    ("human_only", "Human only - on-site, physical, or commercial"),
    ("already_ai", "Already being handled by the AI"),
]

DEFAULT_PROMPT = """You are triaging your OWN work queue for the MSP owner's morning review.

For EVERY ticket you are given, decide its bucket and write what YOU would do next. You are
given the RECENT ACTIVITY on each ticket - read it before you write anything.

HARD RULES, in order of how badly they hurt when broken:

1. READ THE THREAD FIRST. `recent_activity` is what has actually happened, newest first. Your
   answer must be consistent with it. If the thing you were about to suggest has already been
   built, already been tried, or is already running - say THAT instead. Recommending work that
   is already done is the single worst thing this report can do: it tells the reader the
   review did not look.
1a. `original_request` IS STALE BY DEFAULT. It is what the customer asked for when the ticket
   opened, which on an old ticket is mostly history. Where it and `recent_activity` disagree,
   the activity wins. Never present the opening ask as the outstanding work.
1b. RECONCILE ITEM BY ITEM ON MULTI-PART TICKETS. If a technician has enumerated status - "A -
   work completed, B - pending, C - work completed" - that enumeration is the authority. Carry
   it through: say which items are done, and make `what` about the REMAINING item only. Do not
   re-list completed work as if it were outstanding.
1d. SAY WHAT THE TICKET IS FOR, in `purpose`: one plain sentence naming what the customer
   originally wanted, in business terms, for someone who has never seen this ticket. Subjects
   are frequently useless ("IT stuff", "Projects", "Fw: <name>") - the reader needs the intent,
   not the label. `original_request` is STALE for status but it is AUTHORITATIVE for purpose,
   so use it here. On a multi-part ticket, name the parts. No jargon, no restating the subject.
1c. "nothing done yet" IS A CLAIM AND IT IS USUALLY WRONG. Only write it when `recent_activity`
   genuinely contains no work at all - no status update, no note, no reply. On any ticket with
   history, name what was actually done, however briefly.
2. CREDIT PRIOR WORK EXPLICITLY. Fill `already` with one clause naming what has been
   established or done so far (by a tech or by you), and `what` with the NEXT step given
   that. If the thread shows nothing was done, say "nothing done yet" in `already`.
3. NO GENERIC TROUBLESHOOTING. If your suggestion is the first step of a vendor
   documentation page, it is wrong. The thread has usually already passed that point. Name
   the specific check, file, command, query or report that comes NEXT.
4. DESCRIBE WHAT YOU CAN ACTUALLY DO. You act through the RMM agent - you run commands and
   read logs and files on managed devices - and through the helpdesk. You do not "remote in",
   you do not click through GUIs, you have no Microsoft 365 or vendor-portal access, and you
   cannot touch a device with no agent. Do not describe a human's workflow as if it were
   yours.
5. BLOCKERS MUST NAME WHO DOES WHAT. "Needs approval" is useless. "Needs a window on a live
   file server - it has active SMB sessions" is useful. If nothing blocks you, say "nothing".
6. IF IT IS ALREADY DONE OR ALREADY YOURS, BUCKET IT THAT WAY. `already_ai` when you are
   producing the deliverable, and say what you are producing and how often.

Buckets:
  ai_now         - you could finish it today with nothing but an approval to send or act.
  ai_one_step    - you can do the technical work; a human must do exactly one thing.
  blocked_access - you have a runbook but no hands (Microsoft 365, a vendor portal, no agent).
  value_only     - a third party or hardware owns the outcome; you can still add evidence.
  human_only     - on-site, physical, or commercial. Say plainly why it is not yours.
  already_ai     - you are already doing this one.

Also set `waiting_on_note` when the ticket is stalled on the customer, so the reader can
chase rather than work it. Never invent a device, a customer or an access path. One entry per
ticket, nothing left out."""


def _fallback_bucket(f: Dict[str, Any]) -> str:
    """Deterministic bucketing, used when the model is off or unavailable."""
    if f.get("last_msg_bot") and f.get("known_condition"):
        return "already_ai"
    if f["hint_human"] and not f["agents_online"]:
        return "human_only"
    if f["hint_m365"] and not f["hint_human"]:
        return "blocked_access"
    if f["hint_third_party"]:
        return "value_only"
    if f["agents_online"] and (f["procedures"] or f["known_condition"]):
        return "ai_one_step"
    if f["agents_online"]:
        return "ai_now"
    if not f["rmm_client"]:
        return "value_only"
    return "human_only"


def classify(facts: List[Dict[str, Any]], core, options: Dict[str, Any] = None) -> Dict[str, Any]:
    """Bucket + phrase. Model when enabled, deterministic fallback otherwise."""
    opts = options or {}
    want = opts.get("ai_summary")
    if want is None:
        want = bool(core.ai_ticket_review_ai_summary)
    if not want:
        return {"items": {f["ref"]: {"bucket": _fallback_bucket(f), "purpose": "", "what": "", "blocker": ""}
                          for f in facts}, "by": "rules"}

    import requests as _requests

    from core.tasks import _resolve_ai_model

    model = _resolve_ai_model(None)
    if not model:
        return {"items": {f["ref"]: {"bucket": _fallback_bucket(f), "purpose": "", "what": "", "blocker": ""}
                          for f in facts}, "by": "rules (no model configured)"}

    payload = [{
        "ref": f["ref"], "subject": f["subject"][:300], "customer": f.get("company_name", ""),
        "requester": f.get("person_name", "") or f.get("requester_email", ""),
        "stage": f.get("stage", ""), "assignee": f.get("assignee", ""),
        "age_days": f["age_days"], "rmm_client": f["rmm_client"],
        "agents": f["agents"], "agents_online": f["agents_online"],
        "triage": f["triage"], "matched_procedures": [p["title"] for p in f["procedures"]],
        "known_condition": f["known_condition"],
        "original_request": (f.get("body") or "")[:900],
        "messages_total": f.get("msg_count", 0),
        "waiting_on": f.get("waiting_on", ""),
        # THE most important field: what has actually happened on this ticket. Judging a
        # 13-day-old ticket by its opening paragraph is how a review recommends step one of a
        # vendor doc on a ticket where three days of work already happened - or recommends
        # BUILDING a monitoring stack that has been running and reporting daily for a week.
        # Cleaned deployment-side: the reply template's "Original Request" tail is stripped,
        # auto-acknowledgements and near-duplicate re-posts are dropped, so these slots carry
        # substance rather than boilerplate.
        "recent_activity": [
            {"when": m.get("date", "")[:16], "who": m.get("author", ""), "what": (m.get("text") or "")[:700]}
            for m in (f.get("recent_messages") or [])
        ],
    } for f in facts]

    bridge = getattr(settings, "PI_BRIDGE_URL", "http://127.0.0.1:8787")
    prompt = (str(opts.get("prompt") or "").strip()
              or (core.ai_ticket_review_prompt or "").strip()
              or DEFAULT_PROMPT)
    extra = str(opts.get("prompt_extra") or "").strip()
    if extra:
        prompt += ("\n\nADDITIONAL INSTRUCTIONS FOR THIS REPORT (from whoever scheduled it - "
                   "follow them in addition to everything above):\n" + extra)
    content = (
        "Return ONLY JSON: {\"items\":[{\"ref\":\"TICKET/1\",\"bucket\":\"ai_now\","
        "\"purpose\":\"what the ticket was originally for, one plain sentence\","
        "\"already\":\"what has been done so far\",\"what\":\"the NEXT step you would take\","
        "\"blocker\":\"who must do what, or 'nothing'\",\"waiting_on_note\":\"\"}]} "
        "with one entry per ticket, no prose.\n\n"
        "TICKETS (facts gathered from RMM, the triage record and the procedure library - "
        "treat them as authoritative and do not contradict them):\n" + json.dumps(payload)
    )
    try:
        r = _requests.post(
            f"{bridge}/pi/analyze",
            json={"provider": model.provider.name, "model_id": model.model_id,
                  "api_key": model.provider.api_key, "base_url": model.provider.base_url,
                  "thinking_level": model.thinking_level,
                  "system_prompt": prompt, "content": content},
            timeout=(10, 900),
        ).json()
        raw = r.get("text") or r.get("output") or ""
        m = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(m.group(0)) if m else {}
        items = {}
        valid = {b for b, _ in BUCKETS}
        for it in data.get("items", []):
            ref = it.get("ref")
            if not ref:
                continue
            b = it.get("bucket") if it.get("bucket") in valid else None
            items[ref] = {"bucket": b or _fallback_bucket(
                next((f for f in facts if f["ref"] == ref), {"hint_human": False, "hint_m365": False,
                                                             "hint_third_party": False, "agents_online": 0,
                                                             "procedures": [], "known_condition": "",
                                                             "rmm_client": ""})),
                          "purpose": str(it.get("purpose") or "")[:400],
                          "already": str(it.get("already") or "")[:500],
                          "what": str(it.get("what") or "")[:900],
                          "blocker": str(it.get("blocker") or "")[:500],
                          "waiting_on_note": str(it.get("waiting_on_note") or "")[:300]}
        for f in facts:  # nothing may be dropped
            items.setdefault(f["ref"], {"bucket": _fallback_bucket(f), "purpose": "", "already": "", "what": "", "blocker": ""})
        return {"items": items, "by": f"{model.provider.name}/{model.model_id}"}
    except Exception as e:
        return {"items": {f["ref"]: {"bucket": _fallback_bucket(f), "purpose": "", "already": "", "what": "", "blocker": ""}
                          for f in facts}, "by": f"rules (model call failed: {str(e)[:120]})"}


TH = ("padding:6px 9px;border:1px solid #ccc;text-align:left;background:#1a3c6e;"
      "color:#fff;font-size:12px")
TD = "padding:7px 9px;border:1px solid #d9dee5;vertical-align:top;font-size:12.5px"
BTN = ("display:inline-block;padding:4px 10px;background:#1a3c6e;color:#ffffff;"
       "text-decoration:none;border-radius:4px;font-size:11.5px;white-space:nowrap")


def render_html(facts: List[Dict[str, Any]], verdicts: Dict[str, Any], *, by: str) -> str:
    byref = {f["ref"]: f for f in facts}
    grouped: Dict[str, List[str]] = {b: [] for b, _ in BUCKETS}
    for ref, v in verdicts.items():
        grouped.setdefault(v["bucket"], []).append(ref)

    def row(ref):
        f, v = byref[ref], verdicts[ref]
        # Client facts come AFTER the purpose: who it is, what they want, then the context
        # needed to judge whether we can act on it.
        facts_line = " &middot; ".join(x for x in [
            f"{f['agents_online']}/{f['agents']} agents online" if f["rmm_client"] else "no RMM client match",
            f"{f['age_days']}d old" if f["age_days"] is not None else "",
            f"{f.get('msg_count', 0)} msgs" if f.get("msg_count") else "",
            f"waiting on {f.get('waiting_on')}" if f.get("waiting_on") else "",
            f["triage"] if f["triage"] != "never triaged" else "",
            ("procedure: " + f["procedures"][0]["title"][:34]) if f["procedures"] else "",
            ("known condition: " + f["known_condition"]) if f["known_condition"] else "",
        ] if x)
        left = (f'<b><a href="{f.get("url","")}" style="color:#0b5cad">{html.escape(ref.replace("TICKET/", "#"))}</a></b>'
                f'<br/><span style="color:#666;font-size:11px">{html.escape(str(f.get("stage","")))}<br/>'
                f'{html.escape(f.get("assignee") or "unassigned")}</span>'
                + (f'<br/><a href="{f["chat_url"]}" style="{BTN}">Work it with AI &#8594;</a>' if f.get("chat_url") else ""))
        who = f'<b>{html.escape((f.get("company_name") or "unknown company")[:38])}</b>'
        person = f.get("person_name") or ""
        email = f.get("requester_email") or ""
        if person or email:
            who += (f'<br/><span style="font-size:12px">{html.escape(person[:34])}'
                    + (f' <span style="color:#888">&lt;{html.escape(email[:38])}&gt;</span>' if email else "")
                    + "</span>")
        purpose = (f'<div style="margin:6px 0 0;font-size:12.5px"><span style="color:#1a3c6e;font-weight:600">For:</span> '
                   f'{html.escape(v["purpose"])}</div>' if v.get("purpose") else "")
        subject = (f'<div style="color:#888;font-size:11px;margin:3px 0 0">subject: '
                   f'{html.escape(f.get("subject","")[:90])}</div>')
        return (f'<tr><td style="{TD};white-space:nowrap">{left}</td>'
                f'<td style="{TD}">{who}{purpose}{subject}'
                f'<div style="color:#888;font-size:10.5px;margin:5px 0 0">{facts_line}</div></td>'
                f'<td style="{TD}">'
                + (f'<span style="color:#5a6b7a;font-size:12px">Already: {html.escape(v["already"])}</span><br/>' if v.get("already") else "")
                + (f'<span style="color:#333">Next: {html.escape(v["what"])}</span>' if v["what"] else "")
                + (f'<br/><span style="color:#8a4b00;font-size:12px">Needs: {html.escape(v["blocker"])}</span>' if v.get("blocker") else "")
                + (f'<br/><span style="color:#1a6b3c;font-size:12px">{html.escape(v["waiting_on_note"])}</span>' if v.get("waiting_on_note") else "")
                + "</td></tr>")

    parts = [
        '<div style="font-family:Segoe UI,Arial,sans-serif;font-size:14px;line-height:1.55;color:#24292f">',
        '<div style="font-weight:700;color:#1a3c6e;font-size:19px;margin:0 0 4px">'
        f'Open ticket review - {len(facts)} open</div>',
        f'<div style="color:#666;font-size:12.5px;margin:0 0 10px">What is on the board and what could come off it. '
        f'Facts (RMM match, reachable agents, matched procedures, age) gathered in code; bucketing and wording by {html.escape(by)}. '
        f'Nothing here has been sent to a customer or changed on a device.</div>',
        '<div style="background:#eef3fa;border:1px solid #c9d8ea;border-radius:5px;padding:9px 12px;font-size:12.5px;margin:0 0 16px">'
        'Ticket numbers link to the helpdesk. <b>Work it with AI</b> opens the chat already bound to that ticket.</div>',
        '<table style="border-collapse:collapse;width:100%;font-size:13px;margin:0 0 8px">'
        f'<tr><th style="{TH}">Bucket</th><th style="{TH}">Count</th></tr>'
        + "".join(f'<tr style="background:{"#fff" if i % 2 == 0 else "#f4f6f9"}">'
                  f'<td style="{TD}">{html.escape(label)}</td><td style="{TD}">{len(grouped.get(b, []))}</td></tr>'
                  for i, (b, label) in enumerate(BUCKETS)) + "</table>",
    ]
    for b, label in BUCKETS:
        refs = grouped.get(b, [])
        if not refs:
            continue
        refs.sort(key=lambda r: -(byref[r]["age_days"] or 0))
        parts.append(f'<div style="font-weight:700;color:#1a3c6e;font-size:16px;margin:22px 0 6px">'
                     f'{html.escape(label)} <span style="color:#666;font-weight:400;font-size:14px">({len(refs)})</span></div>')
        parts.append(f'<table style="border-collapse:collapse;width:100%;margin:6px 0 16px">'
                     f'<tr><th style="{TH}">Ticket</th><th style="{TH}">Company, user &amp; what it is for</th>'
                     f'<th style="{TH}">Where it stands and what I would do</th></tr>'
                     + "".join(row(r) for r in refs) + "</table>")
    parts.append("</div>")
    return "".join(parts)
