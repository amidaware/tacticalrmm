# What this PR gives you — the complete feature list

> **Purpose of this document.** So you can decide whether you want this without reading 20,000
> lines of diff. Everything below is implemented and running on a live MSP desk, not planned.
> Where something is deliberately limited, or cannot be measured honestly, it says so.
>
> Companion docs: **[PI_AI_ASSISTANT.md](PI_AI_ASSISTANT.md)** (setup, API, roles) ·
> `pibridge/` (the sidecar service).

---

## The one-paragraph version

An AI technician that lives inside Tactical RMM. It chats about one device at a time through the
existing agent channel, runs scheduled checks that raise real alerts, and — optionally — works
your helpdesk queue: reading tickets, proving what a device is actually doing, drafting the
customer reply, and closing the ticket when a human tells it to. Everything consequential is
decided by **code**, not by the model: what may be closed, who may be emailed, whether a device
belongs to the customer on the ticket. The model classifies, diagnoses and drafts. A sidecar
service holds the AI runtime so nothing in the Django app blocks on a model call.

---

## 1. Per-device AI chat

Right-click a device → chat window bound to that machine.

| Capability | Detail |
|---|---|
| Runs commands | via the normal `/cmd/` agent path — audited like any other command |
| Runs library scripts | your existing TRMM script library, by id |
| Reads the machine | processes, services, event logs, installed software, checks, tasks, disks, notes |
| Acts on the machine | kill a process, reboot, run a script — each behind an approval |
| Multi-machine sessions | up to 8 devices in one conversation, each with a stated role |
| Model switching mid-chat | keeps the conversation; per-role model permissions apply |
| Resumable history | every chat is stored per device and can be reopened later |
| Read-only mode | a session can be pinned read-only; mutating commands are refused by pattern match |
| Write mode | explicit, per session, and only for roles that hold the permission |
| Auto-approve | optional, remembered per user, and **never** applies to irreversible actions |

**Read-only means "do not change the DEVICE".** Ticket work — replying, noting, closing — is not a
device change and is never gated by it. That distinction is enforced in code and stated in the
model's instructions.

## 2. Scheduled AI tasks (per device)

Recurring checks with a natural-language brief ("verify the backup ran and the store is
reachable"), each producing a structured verdict.

- Verdict is `ok` / `warning` / `alert`; anything but `ok` can raise a **real TRMM alert**.
- Runs headless with a full tool-call transcript recorded — you can read exactly what it ran.
- Dispatch is deduplicated: `next_run` advances **at dispatch**, so a slow run cannot fire twice.
- Each task declares its own **reply register** (`technical` / `general` / `none`), so a task that
  is allowed to talk to a customer says so explicitly, in data.
- Optional per-task model, thinking level, and read-only/mutate posture.

## 3. Bulk AI commands & fleet reports

Ask one question across many machines, get one consolidated answer.

- Select any set of agents (or a whole client/site) and issue one brief.
- Runs in parallel with a concurrency cap; per-device results plus a combined report.
- The finalizer files **one** ticket for the batch (never one per device) via a deterministic
  single-call tool — no fan-out, no duplicates.

## 4. AI ticketing (optional, off by default)

A pipeline, not a prompt. Each stage is code; the model is used only where judgement is wanted.

```
SOURCES → HELPDESK → INTAKE → VERIFY → CLASSIFY → DECIDE ─┬─ CLOSE
                                                          ├─ REPLY (registered)
                                                          └─ ESCALATE → human
```

| Stage | What happens | Who decides |
|---|---|---|
| Intake | scope filter, dedup ledger, internal-notice detection | code |
| Verify | read-only evidence gathered **from the device** before anything is judged | code |
| Classify | alert-clean / alert-actionable / regular / unknown | model |
| Decide | close, cancel, reply, escalate | **code** |
| Draft | the customer-facing words | model |

- **Alert verifiers**: an alert is checked against the machine before it is believed. A
  provably-clean alert is cancelled with its evidence attached and never costs a model call.
- **Ownership proof**: a hostname match is *not* proof. If the device cannot be proven to belong
  to the ticket's customer, the ticket escalates instead of being acted on.
- **Decision chat ("needs input")**: a deep link that opens an AI chat already bound to that
  ticket, with the triage findings, the thread, and the matched runbook loaded.
- **Instructed vs self-directed**: if a technician tells the AI to close or reply, it does — the
  human already decided, and the authorising sentence is written onto the ticket. If the *model*
  wants to close or email on its own initiative, a human is asked every time and no toggle can
  skip it.

## 5. Capability classes — authority as data

Every helpdesk operation carries a class: `read`, `create`, `note`, `knowledge`, `customer`,
`close`, `routing`. Each **surface** holds a set of classes.

| Surface | May do |
|---|---|
| `triage` | read only — holds no mutating operation at all |
| `unattended` (scheduled tasks) | create, note, knowledge, read |
| `auto_resolve` | read, note, knowledge |
| `device_chat` | + customer, routing |
| `decision_chat` | + close (both irreversible classes behind a human confirmation) |
| `mining` | read, knowledge |

**Default deny**: an operation the integration declares as mutating but leaves unclassified is
refused. New operations cannot silently inherit authority. Ships in *warn* mode so a deploy
cannot break a running automation, and flips to *enforce* on evidence.

## 6. Procedures — where the rules live

Vendor knowledge is **data a technician can read and approve**, never hand-written rules in a
code box.

- **Prose half**: symptom, root cause, fix, verification, applies-to keywords, occurrence count.
- **Deterministic half**: a declarative `match` (subject/body patterns and required phrases —
  never an expression), a `condition_key`, an `evidence` mode, a `disposition`, and a
  `repeat_policy`.
- **One generic engine** evaluates approved procedures against every incoming ticket. No vendor
  names anywhere in product code.
- **Mined automatically** from closed tickets (dedup ledger, incremental, never re-processes an
  unchanged ticket), and **capturable from a chat** the moment a technician explains something.
- Anything the model authors arrives as a **draft with automation off**. The model proposes; a
  person promotes. A procedure may only rule by itself once a human has approved it.

See **RULES-MODEL.md** in the project docs repo for the full schema.

## 7. Recurring conditions — advise once, then stop shouting

A daily notification about an unchanged condition is not new work.

- First sighting becomes the **tracker** and stays open for a human.
- Identical repeats are cancelled **against that tracker**, with a note, and never reach the model.
- If a human closes the tracker, the condition is **muted** — repeats stay suppressed and counted,
  but nothing new is raised. Their decision is read as a decision.
- If it stops recurring for N days, the tracker **closes itself** and states what was observed
  ("the notification stopped arriving; this was not verified on the device").
- Two honest evidence modes: go and read the machine, or — where a vendor's report states the
  cause of its own warning — treat the report as the evidence and say so.

## 8. Knowledge that compounds

- **Device notes**: durable per-machine memory. Future runs on that device start with it.
- **Per-client KB**: standards, contacts, conventions, "do not patch these servers".
- Knowledge capture needs no permission and happens proactively, including in read-only sessions —
  writing down what you learned is memory, not a change.

## 9. Reports — operator-defined, any cadence

Reports are rows in a table, not code. Add as many as you like from Global Settings.

| Setting | Options |
|---|---|
| Type | **Activity report** (what happened) · **Open-ticket review** (what could be done) |
| Cadence | daily · weekdays · weekly (pick the day) · monthly (pick the date) |
| Window | 24h / 48h / 72h / 7d / 14d / 30d / follow-the-cadence / any custom hours |
| Recipients | per report |
| Options | all-teams, include-assigned, AI narration on/off |
| Prompt | **extra instructions** added to the default, or a full override for advanced use |

Each schedule resolves its own most-recent occurrence, so a five-minute tick cannot double-send
and a missed window is picked up late rather than skipped silently. "Send now" is one click.

**Activity report** — who did what, how long it took, first-response times, reply quality
samples, closed-without-reply counts, per-technician detail, and an optional AI executive summary
over figures that are always computed in code.

**Open-ticket review** — every open ticket bucketed by *AI can finish it · AI plus one human step ·
blocked by access we do not have · value only · human only · already AI-run*, with each row
linking to the ticket **and** to that ticket's AI chat. It is a work queue you can act from.

## 10. Work ledger — measured time, not guessed time

An append-only record of work, with the rule that produced every number.

| Source | Captures | Confidence |
|---|---|---|
| Ticket chat | AI chat bound to a ticket | `measured` (per-turn timestamps) |
| Device chat | AI chat on a device | `measured` |
| RMM activity | remote sessions, device work, network-device access | `sessionized` |
| Helpdesk direct | replies and notes written by hand | `sessionized` (span **or** content) |

- **A human driving the AI owns that time.** The AI performs writes as the integration's API user,
  so without this the bot gets credit for a technician's afternoon.
- **Parallel work counts in full** — three windows for fifteen minutes is forty-five minutes.
- **Written work counts even with no elapsed time**: three considered replies inside one minute
  span zero seconds but represent real composition, so a burst is valued by span *and* by content
  (characters written and read, at configurable rates) and the larger wins.
- **Corrections are new rows, never edits** — a report already sent still reproduces exactly.
- **Human minutes and AI minutes are never summed.**
- **Time is counted for every ticket touched**, not only tickets that closed.
- **Coverage is reported honestly**: *timed* / *activity seen but not timed* / *no activity
  recorded*, so a quiet day is never presented as a lazy one. Phone calls, on-site visits and
  third-party consoles leave no trace anywhere and the report says so rather than implying zero.
- Staff are identified by **mail domain**, so a customer with a portal login never appears as one
  of your technicians. Identity is the **user id**, so a rename does not fork someone's history.

## 11. Model catalog, registration & self-update

- Providers and models are configured in the database; keys never leave it.
- The catalog is compared against **what the provider actually offers today**, not just what the
  installed runtime knows — a model released this morning can be made usable the same day.
- A registration is **temporary by construction**: once the runtime learns that model natively, the
  local stub is pruned on boot. (A stale stub once shadowed a real definition and made every call
  to that model fail — this is why.)
- Optional nightly runtime self-update with a **compatibility probe** and automatic rollback, gated
  on quiescence: it refuses while any chat, run, mining job or triage is in flight.

## 12. Governance, safety and auditability

- **Never deletes customer data.** No exception anywhere in the codebase.
- **Never reboots, stops a service or takes anything offline** without explicit approval at the time.
- **Identity/access actions** (accounts, groups, licences, mailboxes, passwords, MFA) require the
  requester to be an approved support contact — enforced in code, not by prompt, and not bypassable
  by any toggle.
- **Every automatic decision is auditable**: the evidence is posted to the ticket with the action.
- **New automatic behaviour ships in dry run first**, proving itself on real tickets while changing
  nothing.
- Provider rejections are surfaced, not swallowed — a 4xx from a model provider appears in the log
  *and* in the operator's window rather than looking like "the AI just didn't answer".
- Full tool-call transcripts for unattended runs; outbound customer text is recorded before it is
  sent.

## 13. Roles & permissions

Per-role: use AI · write/mutate · auto-approve · manage all AI tasks · which models are permitted.
Superusers get everything. A model a role may not use cannot be selected, and the session refuses
it server-side rather than hiding it in the UI.

## 14. What it deliberately does NOT do

- No Microsoft 365 / vendor-portal actions (no hands there — it will tell you so instead of guessing).
- No commercial, contractual or billing decisions.
- No acting on a device it cannot prove belongs to the ticket's customer.
- No closing a person-filed ticket without a customer reply.
- No customer contact at all for conditions that do not require the customer to do anything.
- No promise of dates, dispatch times or turnaround in customer replies.
- No timesheet claims for work that leaves no trace — it reports the gap instead.

## 15. Deployment shape

- One extra service: **`pibridge`** (Node sidecar, systemd unit + `setup.sh`) on the RMM host,
  listening on localhost only, reverse-proxied for the WebSocket chat.
- Django side: models, tasks, endpoints and settings — all inside the existing app.
- Deployment-specific integration code (helpdesk API glue, verifier rules, prompts) lives in the
  **database**, authored per install, and is never committed here. Nothing customer-specific ships
  in this PR.

## 16. How to evaluate it safely

1. Install the bridge, add one provider and one model, grant yourself the AI role permissions.
2. Use the **device chat** in read-only mode on a lab machine. Watch the tool calls.
3. Add one **scheduled AI task** against that machine. Let it raise one alert.
4. Leave ticketing **off**. When you turn it on, it starts in look-only shadow mode: it writes an
   internal note describing what it *would* do, and changes nothing.
5. Turn on **alert verifiers in dry run**: they report the verdict they *would* have acted on.
6. Flip capability enforcement from **warn** to **enforce** only after reading a day of warn lines.
7. Add a **report schedule** for the last 24 hours and read what it says about your own desk.

Each step is reversible and each one produces evidence you can check before granting the next.
