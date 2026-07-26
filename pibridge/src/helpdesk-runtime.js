// Loads and runs the admin-authored "helpdesk.js" integration code that lives
// in Global Settings (CoreSettings.ai_helpdesk_code). This is what makes the
// ticketing layer BOTH deterministic (real code) AND system-agnostic (the code
// is written per-deployment for Odoo / Zendesk / Freshdesk / anything).
//
// Trust model: this runs admin-supplied JS on the bridge host. Only users with
// can_edit_core_settings can set it - the same trust level as TRMM's script
// library (which already runs arbitrary code on every managed device). node:vm
// is used to scope the globals it sees, NOT as a hard security sandbox.
//
// CONTRACT (what the admin code writes):
//   // In scope: helpdesk = { baseUrl, apiKey }, fetch, console, URL,
//   //           URLSearchParams, TextEncoder, TextDecoder, Buffer, atob, btoa,
//   //           setTimeout, clearTimeout.
//   // Define async operations the AI can call, and (optionally) describe them.
//   exports.operations = {
//     async resolve_customer({ name }) { ... return { id, name } },
//     async create_ticket({ customer, subject, body }) { ... return { ref } },
//     async reply_to_ticket({ ticket, message }) { ... },
//     async add_note({ ticket, message }) { ... },
//     async submit_report({ subject, body, partner_id, team_id }) { ... },
//   };
//   exports.meta = { create_ticket: "Create a new ticket", ... };   // optional
//   exports.mutating = ["create_ticket","reply_to_ticket","add_note","submit_report"]; // optional
//   // Capability class per operation - what AUTHORITY it carries. Product code maps
//   // surfaces to allowed classes (see capabilities.js); anything declared mutating
//   // but left unclassified is DENIED on unattended surfaces (default deny).
//   // One of: read | create | note | knowledge | customer | close | routing
//   exports.opClasses = { create_ticket: "create", reply_to_ticket: "customer",
//                         cancel_ticket: "close", add_note: "note", ... };  // optional but recommended
import vm from "node:vm";

export function loadHelpdesk(code, config, context) {
  if (!code || !code.trim()) return null;
  const exportsObj = {};
  const sandbox = {
    exports: exportsObj,
    module: { exports: exportsObj },
    // helpdesk.context is present for SINGLE-device sessions: { deviceUrl,
    // hostname, client, site, agentId } - so the integration can put a deep
    // link to the device in the ticket. Empty object for multi-device/report.
    helpdesk: {
      baseUrl: (config?.base_url || "").replace(/\/+$/, ""),
      apiKey: config?.api_key || "",
      context: context || {},
    },
    fetch,
    console: { log: () => {}, error: () => {}, warn: () => {} },
    URL,
    URLSearchParams,
    TextEncoder,
    TextDecoder,
    Buffer,
    atob,
    btoa,
    setTimeout,
    clearTimeout,
    JSON,
  };
  vm.createContext(sandbox);
  // Only top-level (synchronous) setup is time-boxed; async ops run later.
  vm.runInContext(code, sandbox, { timeout: 5000, filename: "helpdesk.js" });

  const ex = sandbox.module.exports && Object.keys(sandbox.module.exports).length
    ? sandbox.module.exports
    : sandbox.exports;
  const operations = ex.operations || {};
  const names = Object.keys(operations).filter((k) => typeof operations[k] === "function");
  if (!names.length) throw new Error("helpdesk.js defined no exports.operations functions");
  return {
    operations,
    names,
    meta: ex.meta || {},
    mutating: new Set(ex.mutating || names), // default: treat all as mutating (safe)
    // Capability tags. Absent -> product code falls back to its name-based default
    // classifier, and anything it cannot classify is denied where authority matters.
    opClasses: ex.opClasses || {},
    apiKey: sandbox.helpdesk.apiKey,
  };
}
