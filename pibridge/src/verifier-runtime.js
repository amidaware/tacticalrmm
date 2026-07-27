// Loads and runs the admin-authored "verifiers.js" code box that lives in Global
// Settings (CoreSettings.ai_verifier_code).
//
// WHY THIS EXISTS: machine-generated alert tickets ("backup successful - 0 B",
// "disk check failed", "service stopped") frequently describe a NON-problem, and
// just as often hide a REAL one. Deciding which is which from the alert TEXT is
// guesswork - you have to go look at the box. A verifier does exactly that, and the
// decision is made in CODE, never by the language model:
//
//   match(ticket)  -> is this my kind of alert?
//   host(ticket)   -> which machine should I inspect?
//   script         -> a READ-ONLY evidence script to run on it
//   verdict(ev)    -> deterministic ruling from that evidence
//
// A verdict is one of:
//   noise      - proven harmless; safe to auto-cancel (evidence is attached)
//   actionable - proven to be a real problem; stays open, says exactly what is wrong
//   human      - could not prove either way; leave for a person (the safe default)
//
// Trust model: identical to helpdesk.js - admin-supplied JS running on the bridge
// host, settable only by users with can_edit_core_settings. node:vm scopes the
// globals it sees; it is NOT a hard security sandbox.
//
// CONTRACT (what the admin code writes):
//   exports.verifiers = [{
//     name: "Proxmox vzdump backup report",
//     enabled: true,                // optional, default true; false = parked/template
//     match:  (t) => /vzdump backup status/i.test(t.subject),
//     host:   (t) => (t.subject.match(/\(([^)]+)\)/) || [])[1] || "",
//     shell:  "/bin/bash",          // optional: /bin/bash | /bin/sh | powershell | cmd
//     identity: "hostname -f",      // optional: how this kind of box states its own
//                                   //   FQDN, used to prove we found the right machine.
//                                   //   Defaults sensibly from `shell`.
//     timeout: 60,                  // optional, seconds
//     script: "pvesh get /cluster/resources ...",   // READ-ONLY commands only
//     verdict: (ev) => ({ action: "noise", reason: "...", detail: "..." }),
//   }];
//
// SELF-PROVING rules: set `evidence: "ticket"` when the notification itself states the
// cause of its own warning (a vendor job report saying "skipped X because Y is disabled").
// No host resolution and no device script run; `verdict({stdout:"", ticket, host})` is
// called directly. Use it ONLY where the report is the evidence - never to save a lookup
// on an alert whose truth lives on the box.
//
// RECURRING conditions: a verdict may additionally return
//   condition_key: "vendor-thing-that-is-wrong"   // stable key for THIS condition
//   condition_host: "HOSTNAME"                    // which box it is about
//   advise_once: true                             // default true
//   fix_summary: "what the customer must do"
// Product code then owns the repeat policy (tell the customer once, track it, suppress
// identical repeats against the tracker, stand down when it stops). The rule names the
// condition; it does not decide the policy.
import vm from "node:vm";

export function loadVerifiers(code) {
  if (!code || !code.trim()) return null;
  const exportsObj = {};
  const sandbox = {
    exports: exportsObj,
    module: { exports: exportsObj },
    console: { log: () => {}, error: () => {}, warn: () => {} },
    JSON, Math, Date, RegExp, Number, String, Boolean, Array, Object,
    parseInt, parseFloat, isNaN, encodeURIComponent, decodeURIComponent,
  };
  vm.createContext(sandbox);
  vm.runInContext(code, sandbox, { timeout: 5000, filename: "verifiers.js" });
  const ex = sandbox.module.exports && Object.keys(sandbox.module.exports).length
    ? sandbox.module.exports
    : sandbox.exports;
  const list = Array.isArray(ex.verifiers) ? ex.verifiers : [];
  // A rule may be parked with `enabled: false` - useful for staging a new alert type,
  // or keeping a worked-out template on the shelf, without it claiming live tickets.
  const valid = list.filter((v) => v && v.enabled !== false
    && typeof v.match === "function" && typeof v.verdict === "function");
  if (!valid.length) throw new Error("verifiers.js defined no valid exports.verifiers (need match + verdict)");
  return { verifiers: valid, names: valid.map((v) => v.name || "(unnamed)") };
}

// Pick the FIRST verifier that claims this ticket. A throwing match() never
// takes down the run - a broken rule is simply skipped.
export function matchVerifier(loaded, ticket) {
  if (!loaded) return null;
  for (const v of loaded.verifiers) {
    try { if (v.match(ticket)) return v; } catch { /* a bad rule must not block triage */ }
  }
  return null;
}

// Inspect a rule set for the settings UI WITHOUT running anything: lists every rule
// (including parked ones, which loadVerifiers deliberately hides) plus whatever is
// structurally wrong with it, so a rule can be authored without guessing.
export function inspectVerifiers(code) {
  if (!code || !code.trim()) return { ok: true, rules: [], note: "No verifier code - nothing will be verified." };
  const exportsObj = {};
  const sandbox = {
    exports: exportsObj, module: { exports: exportsObj },
    console: { log: () => {}, error: () => {}, warn: () => {} },
    JSON, Math, Date, RegExp, Number, String, Boolean, Array, Object,
    parseInt, parseFloat, isNaN, encodeURIComponent, decodeURIComponent,
  };
  try {
    vm.createContext(sandbox);
    vm.runInContext(code, sandbox, { timeout: 5000, filename: "verifiers.js" });
  } catch (e) {
    return { ok: false, error: String(e?.message || e), rules: [] };
  }
  const ex = sandbox.module.exports && Object.keys(sandbox.module.exports).length
    ? sandbox.module.exports : sandbox.exports;
  if (!Array.isArray(ex.verifiers))
    return { ok: false, error: "exports.verifiers is missing or not an array", rules: [] };
  const rules = ex.verifiers.map((v, i) => {
    const problems = [];
    if (!v || typeof v !== "object") problems.push("not an object");
    else {
      if (typeof v.match !== "function") problems.push("missing match(ticket)");
      if (typeof v.verdict !== "function") problems.push("missing verdict(evidence)");
      if (typeof v.host !== "function") problems.push("no host(ticket) - cannot pick a device to inspect");
      if (!String(v.script || "").trim()) problems.push("no script - no evidence would be gathered");
    }
    return {
      index: i,
      name: (v && v.name) || `(unnamed #${i + 1})`,
      enabled: !(v && v.enabled === false),
      shell: (v && v.shell) || "/bin/bash",
      identity: (v && v.identity) || "(default for shell)",
      timeout: (v && v.timeout) || 60,
      script_lines: String((v && v.script) || "").split("\n").filter((l) => l.trim()).length,
      problems,
    };
  });
  const live = rules.filter((r) => r.enabled && !r.problems.length).length;
  return { ok: true, rules, live, total: rules.length };
}
