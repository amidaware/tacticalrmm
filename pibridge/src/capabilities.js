// capabilities.js - WHO may do WHAT to a ticket. Single source of truth.
//
// Why this exists (ISSUES.md F1): every surface that built a toolset used to attach
// the FULL helpdesk operation list, and unattended runs passed gate: () => true. So a
// scheduled job could reply to a customer, close, cancel, resolve or re-attribute ANY
// ticket, restrained only by prompt prose. MANDATE 4.8 requires the consequential
// decision to live in code ("the model never decides that a ticket may be closed").
//
// The portable unit is a CAPABILITY CLASS, not an operation name. Operation names are
// authored per deployment in helpdesk.js, so an allow-list of names in product code
// would break MANDATE 4.11 (helpdesk-agnostic product code) - it would silently
// protect nothing on a deployment that named its operations differently. Classes are
// declared by the deployment and consumed by product code.
//
// DEFAULT DENY: an operation the deployment declares as mutating, but does not
// classify, is DENIED. A new operation can never silently inherit authority.

// The seven classes. Anything outside this set is treated as unclassified (denied).
export const CLASSES = ["read", "create", "note", "knowledge", "customer", "close", "routing"];

// Ships-working-out-of-the-box classifier for conventional operation names. This is a
// DEFAULT CLASSIFIER ONLY, never the authority: explicit exports.opClasses always wins.
// An unrecognised name is not an error - it falls through to the mutating check below.
export const NAME_DEFAULTS = {
  // read
  get_ticket: "read", get_ticket_stages: "read", list_open_tickets: "read",
  list_closed_tickets: "read", find_company: "read", resolve_customer: "read",
  resolve_client_by_domain: "read", check_support_authorization: "read",
  get_kb_article: "read", list_kb_articles: "read", get_global_kb: "read",
  // create
  create_ticket: "create", submit_report: "create",
  // note
  add_note: "note",
  // knowledge  (MANDATE 4.13: knowledge capture is memory, not a change)
  upsert_ai_kb_article: "knowledge",
  // customer  (irreversible outbound contact)
  reply_to_ticket: "customer",
  // close
  cancel_ticket: "close", close_ticket: "close", ai_close_ticket: "close",
  resolve_ticket: "close",
  // routing
  assign_ticket: "routing", assign_to_working_user: "routing", claim_ticket: "routing",
  release_ticket: "routing", add_follower: "routing", set_ticket_company: "routing",
  set_needs_input_tag: "routing", clear_needs_input_tag: "routing",
};

// Surface -> allowed classes. The surface is WHERE the model is running, which
// determines how much human oversight exists at the moment it acts.
//
// NOTE: runAlertVerify is deliberately absent. It calls hd.operations.cancel_ticket
// DIRECTLY from code on proven device evidence, with no LLM tool surface at all - it
// is already the deterministic, code-owned decision MANDATE 4.8 asks for. Gating it
// here would gate code against itself.
export const SURFACE_CLASSES = {
  // Unattended: AI Tasks, bulk per-device runs, scheduled actions. No human present,
  // so no irreversible customer contact and no closing authority.
  unattended:    ["create", "note", "knowledge", "read"],
  // End-of-batch report finalizer. Files ONE combined ticket.
  report:        ["create", "read"],
  // Interactive device chat: a human is watching and approves each mutating call.
  device_chat:   ["create", "note", "knowledge", "read", "customer", "routing"],
  // Decision chat: a human is driving the ticket and approves each mutating call.
  decision_chat: ["create", "note", "knowledge", "read", "customer", "routing", "close"],
  // Ticket Console auto-resolve: read-only investigation, posts a note. Never closes,
  // never emails. Replaces the old blockOps name list (ISSUES.md I6).
  auto_resolve:  ["read", "note", "knowledge"],
  // Classification only - holds no mutating tools at all.
  triage:        ["read"],
  // Learning: reads closed tickets, writes only to our own stores.
  mining:        ["read", "knowledge"],
};

// "warn"    - log what WOULD be denied, allow it through (observation window)
// "enforce" - actually refuse
// Default is warn so a deploy cannot silently break a running automation; flip to
// enforce once a day of real dispatches has been reviewed (MANDATE 4.10 in spirit).
export const CAPS_MODE = (process.env.PI_CAPS_MODE || "warn").toLowerCase() === "enforce"
  ? "enforce"
  : "warn";

function stamp(...a) {
  console.log(new Date().toISOString(), ...a);
}

// Resolve an operation to a class.
//   1. explicit deployment tag (exports.opClasses)  <- the authority
//   2. product-code name default                    <- convenience
//   3. null                                         <- unclassified
export function classOf(op, opClasses) {
  const tagged = opClasses && opClasses[op];
  if (tagged && CLASSES.includes(tagged)) return tagged;
  const named = NAME_DEFAULTS[op];
  if (named) return named;
  return null;
}

// Where a class came from - surfaced in validation UI so an admin can see what product
// code guessed versus what the deployment declared.
export function classSource(op, opClasses) {
  const tagged = opClasses && opClasses[op];
  if (tagged && CLASSES.includes(tagged)) return "declared";
  if (tagged) return "invalid";
  if (NAME_DEFAULTS[op]) return "name-guess";
  return "unclassified";
}

// THE decision. Returns { allowed, cls, reason }.
//
// An unknown surface denies every mutating class - fail safe, and it means a new
// endpoint cannot invent its own permission model by forgetting to declare itself.
export function checkOp({ surface, op, opClasses, mutating }) {
  const allowedClasses = SURFACE_CLASSES[surface];
  const isMutating = mutating ? mutating.has(op) : true; // unknown -> assume mutating
  let cls = classOf(op, opClasses);

  // An operation the deployment does NOT declare as mutating changes nothing by its
  // own declaration, so an unclassified one is treated as a read rather than denied.
  // This keeps lookups working out of the box without weakening the authority check:
  // default-deny applies to anything declared mutating. Note helpdesk-runtime.js
  // defaults `mutating` to ALL operation names when exports.mutating is absent, so a
  // deployment that declares nothing gets the strict path, not the lenient one.
  if (!cls && !isMutating) cls = "read";

  if (!allowedClasses) {
    return { allowed: false, cls, reason: `surface '${surface}' is not a known capability surface` };
  }
  if (!cls) {
    return {
      allowed: false, cls: null,
      reason: `'${op}' is not classified. Tag it in helpdesk.js (exports.opClasses) with one of: ${CLASSES.join(", ")}`,
    };
  }
  if (!allowedClasses.includes(cls)) {
    return {
      allowed: false, cls,
      reason: `'${op}' is a '${cls}' operation, which is not permitted on the '${surface}' surface (allowed: ${allowedClasses.join(", ")})`,
    };
  }
  return { allowed: true, cls, reason: "" };
}

// Enforcement wrapper. Logs every denial either way so the warn-mode window produces
// the evidence needed before switching to enforce.
export function gateOp(ctx) {
  const v = checkOp(ctx);
  if (v.allowed) return v;
  stamp(
    `caps_${CAPS_MODE === "enforce" ? "deny" : "warn"}>`,
    `surface=${ctx.surface}`, `op=${ctx.op}`, `class=${v.cls || "unclassified"}`,
    `ref=${ctx.ref || "-"}`, `| ${v.reason}`,
  );
  return { ...v, enforced: CAPS_MODE === "enforce" };
}

// Operations this surface may actually call - used to filter the list advertised to
// the model, so it is not shown authority it does not have. Enforcement still happens
// at execute time: filtering the description is not a control, since the model can
// name an operation it was never shown.
export function allowedOps({ surface, names, opClasses, mutating }) {
  return (names || []).filter((op) => checkOp({ surface, op, opClasses, mutating }).allowed);
}
