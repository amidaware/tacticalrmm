// Model availability: what the PROVIDER actually offers today, merged with what the
// installed pi package knows how to run.
//
// WHY THIS EXISTS: pi's ModelRegistry.getAvailable() returns the model list BUNDLED
// WITH THE INSTALLED PACKAGE (plus models.json). It never asks the provider. So a
// model released this morning is invisible until the package is upgraded, and a model
// the provider retired stays in the list forever. Both are exactly what the catalog
// watch was built to catch, so discovery has to ask the provider directly.
//
// Two questions, deliberately kept separate:
//   AVAILABLE - does the provider serve this model id today?   (their API answers)
//   USABLE    - can the installed pi run it?                   (registry.find answers)
// A model can be available-but-not-usable (new upstream, package doesn't know it yet).
// That is a fixable state: registerModels() writes it into models.json, which pi merges
// into built-in providers, and it becomes usable WITHOUT a package upgrade.
import fs from "node:fs";
import path from "node:path";

// Where custom/extra model definitions live. Passed to ModelRegistry.create() by
// newRegistry() in server.js, so every surface (chat, headless, triage) sees them.
export const MODELS_JSON = process.env.PI_MODELS_JSON
  || path.join(process.env.PI_BRIDGE_DIR || "/opt/pi-trmm-bridge", "models.json");

const TIMEOUT_MS = 20000;

async function getJson(url, headers) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const r = await fetch(url, { headers, signal: ctrl.signal });
    const text = await r.text();
    let data = null;
    try { data = JSON.parse(text); } catch { /* non-JSON error page */ }
    if (!r.ok) {
      const msg = (data && (data.error?.message || data.message)) || text.slice(0, 200);
      return { error: `HTTP ${r.status}: ${msg}` };
    }
    return { data };
  } catch (e) {
    return { error: String(e?.name === "AbortError" ? "timed out" : (e?.message || e)) };
  } finally {
    clearTimeout(t);
  }
}

// Per-provider "what do you offer" call. Unknown provider names fall through to the
// OpenAI-compatible /v1/models shape, which most gateways implement.
async function fetchProviderModels(prov) {
  const name = String(prov.name || "").toLowerCase();
  const key = prov.api_key || "";
  const base = String(prov.base_url || "").replace(/\/+$/, "");
  if (!key) return { error: "no api key configured" };

  if (name === "anthropic") {
    const url = (base || "https://api.anthropic.com") + "/v1/models?limit=1000";
    const { data, error } = await getJson(url, { "x-api-key": key, "anthropic-version": "2023-06-01" });
    if (error) return { error };
    return { models: (data?.data || []).map((m) => ({ id: m.id, name: m.display_name || m.id })) };
  }
  if (name === "google" || name === "gemini" || name === "google-generative-ai") {
    const url = (base || "https://generativelanguage.googleapis.com/v1beta") + "/models?key=" + encodeURIComponent(key);
    const { data, error } = await getJson(url, {});
    if (error) return { error };
    return {
      models: (data?.models || [])
        .map((m) => ({ id: String(m.name || "").replace(/^models\//, ""), name: m.displayName || m.name }))
        .filter((m) => m.id),
    };
  }
  // openai, xai, openrouter, deepseek, groq, mistral, custom gateways...
  const defaults = {
    openai: "https://api.openai.com/v1",
    xai: "https://api.x.ai/v1",
    openrouter: "https://openrouter.ai/api/v1",
    deepseek: "https://api.deepseek.com/v1",
    groq: "https://api.groq.com/openai/v1",
    mistral: "https://api.mistral.ai/v1",
  };
  const root = base || defaults[name];
  if (!root) return { error: `no base_url known for provider "${prov.name}" - set one to enable discovery` };
  const url = root.endsWith("/v1") || /\/v\d/.test(root) ? root + "/models" : root + "/v1/models";
  const { data, error } = await getJson(url, { Authorization: "Bearer " + key });
  if (error) return { error };
  const rows = data?.data || data?.models || [];
  return { models: rows.map((m) => ({ id: m.id || m.name, name: m.name || m.display_name || m.id })).filter((m) => m.id) };
}

// ALIAS AWARENESS. Providers publish undated aliases that their /models endpoint does
// not list (e.g. an alias "x-4-5" served alongside the dated "x-4-5-20251101"). Diffing
// naively reports every alias as retired - a guaranteed false alarm on the first run.
// An id counts as live if the provider lists it, OR it is the stem of something they list.
function isLiveAtProvider(id, providerIds) {
  if (providerIds.has(id)) return true;
  for (const p of providerIds) if (p.startsWith(id + "-")) return true;
  return false;
}

/**
 * Build the merged catalog.
 * @param {Array} providers  [{name, api_key, base_url}]
 * @param {object} registry  a piRuntime() handle (for the USABLE answer)
 * @returns {{models: Array, provider_errors: object, provider_live: object}}
 *   models[]: { provider, model_id, display_name, source: builtin|provider|both,
 *               usable: bool, live_at_provider: bool }
 */
export async function buildCatalog(providers, registry) {
  const known = new Map();          // "provider/id" -> {display_name}
  for (const m of registry.listModels()) known.set(`${m.provider}/${m.model_id}`, m);

  const out = [];
  const errors = {};
  const live = {};
  for (const prov of providers || []) {
    const pname = prov.name;
    const res = await fetchProviderModels(prov);
    if (res.error) errors[pname] = res.error;
    const provList = res.models || [];
    const provIds = new Set(provList.map((m) => m.id));
    live[pname] = [...provIds].sort();

    // Everything pi knows for this provider.
    const builtinIds = [...known.keys()]
      .filter((k) => k.startsWith(pname + "/"))
      .map((k) => k.slice(pname.length + 1));

    const seen = new Set();
    const push = (id, display, inBuiltin, inProvider) => {
      if (seen.has(id)) return;
      seen.add(id);
      // When discovery failed we must not claim anything about provider liveness -
      // an outage would otherwise look like a mass retirement.
      const liveAtProv = res.error ? null : isLiveAtProvider(id, provIds);
      out.push({
        provider: pname,
        model_id: id,
        display_name: display || id,
        source: inBuiltin && inProvider ? "both" : inProvider ? "provider" : "builtin",
        usable: known.has(`${pname}/${id}`),
        live_at_provider: liveAtProv,
      });
    };
    for (const m of provList) push(m.id, m.name, known.has(`${pname}/${m.id}`), true);
    for (const id of builtinIds) push(id, known.get(`${pname}/${id}`)?.display_name || id, true, provIds.has(id));
  }
  return { models: out, provider_errors: errors, provider_live: live };
}

/**
 * Drop models.json entries that the installed pi now knows NATIVELY.
 *
 * WHY: an entry written by registerModels() is a minimal stub (no `compat`, no
 * `thinkingLevelMap`, default context/cost). models.json takes precedence over the
 * built-in table, so once a pi upgrade ships a real definition for that id, the old
 * stub SHADOWS it and silently downgrades the model. Observed live: a registered
 * `anthropic/claude-opus-5` stub masked the built-in
 * `compat.forceAdaptiveThinking`, so every Opus 5 request was rejected by Anthropic
 * with 400 "thinking.type.enabled is not supported for this model" - the chat just
 * ended with an empty answer. Registration is meant to be a temporary bridge until
 * the package catches up, so it must expire by itself.
 *
 * @param {(provider:string,id:string)=>Promise<any>} isBuiltin  pi-runtime's builtinModel
 * @returns {{pruned: string[], file: string, error?: string}}
 */
export async function pruneShadowedModels(isBuiltin) {
  if (!fs.existsSync(MODELS_JSON)) return { pruned: [], file: MODELS_JSON };
  let conf;
  try {
    conf = JSON.parse(fs.readFileSync(MODELS_JSON, "utf-8"));
  } catch (e) {
    return { pruned: [], file: MODELS_JSON, error: `${MODELS_JSON} is not valid JSON (${String(e?.message || e)})` };
  }
  if (!conf || typeof conf !== "object" || !conf.providers) return { pruned: [], file: MODELS_JSON };
  const pruned = [];
  for (const [pname, pconf] of Object.entries(conf.providers)) {
    if (!pconf || !Array.isArray(pconf.models)) continue;
    const keep = [];
    for (const m of pconf.models) {
      if (!m?.id) continue;
      // The normal lookup resolves through models.json too, so it would report our own
      // stub as "known". isBuiltin() asks the package alone.
      if (await isBuiltin(pname, m.id)) { pruned.push(`${pname}/${m.id}`); continue; }
      keep.push(m);
    }
    pconf.models = keep;
    if (!pconf.models.length) delete conf.providers[pname];
  }
  if (pruned.length) {
    const tmp = MODELS_JSON + ".tmp";
    fs.writeFileSync(tmp, JSON.stringify(conf, null, 2) + "\n");
    fs.renameSync(tmp, MODELS_JSON);
  }
  return { pruned, file: MODELS_JSON };
}

/**
 * Make provider models that pi does not know natively USABLE, by adding them to
 * models.json under the (built-in) provider - pi inherits api + baseUrl from the
 * provider's built-in models, so no endpoint or key duplication is needed.
 *
 * Guard: only ids the provider itself just confirmed are written. We never invent a
 * model id, and we never touch an entry pi already knows.
 */
export async function registerModels(providers, registry, wanted) {
  const byProv = new Map();
  for (const w of wanted || []) {
    if (!w?.provider || !w?.model_id) continue;
    if (!byProv.has(w.provider)) byProv.set(w.provider, []);
    byProv.get(w.provider).push(w);
  }
  if (!byProv.size) return { registered: [], skipped: [], file: MODELS_JSON };

  let conf = { providers: {} };
  try {
    if (fs.existsSync(MODELS_JSON)) {
      const parsed = JSON.parse(fs.readFileSync(MODELS_JSON, "utf-8"));
      if (parsed && typeof parsed === "object") conf = parsed;
      if (!conf.providers || typeof conf.providers !== "object") conf.providers = {};
    }
  } catch (e) {
    return { error: `existing ${MODELS_JSON} is not valid JSON (${String(e?.message || e)}) - refusing to overwrite it` };
  }

  const registered = [], skipped = [];
  for (const [pname, list] of byProv.entries()) {
    const prov = (providers || []).find((p) => p.name === pname);
    if (!prov) { for (const w of list) skipped.push({ ...w, reason: "provider not configured here" }); continue; }
    // Re-confirm against the provider before writing anything.
    const res = await fetchProviderModels(prov);
    if (res.error) { for (const w of list) skipped.push({ ...w, reason: `provider re-check failed: ${res.error}` }); continue; }
    const offered = new Map((res.models || []).map((m) => [m.id, m.name]));
    if (!conf.providers[pname] || typeof conf.providers[pname] !== "object") conf.providers[pname] = {};
    const pconf = conf.providers[pname];
    if (!Array.isArray(pconf.models)) pconf.models = [];
    for (const w of list) {
      const id = w.model_id;
      if (!offered.has(id)) { skipped.push({ ...w, reason: "provider does not offer this id" }); continue; }
      if (registry.findModel(pname, id)) { skipped.push({ ...w, reason: "pi already knows this model" }); continue; }
      if (pconf.models.some((m) => m && m.id === id)) { skipped.push({ ...w, reason: "already in models.json" }); continue; }
      pconf.models.push({
        id,
        name: w.display_name || offered.get(id) || id,
        // Conservative defaults: reasoning on (harmless if unsupported - thinkingLevel
        // "off" is what the callers pass unless a model row says otherwise) and the
        // common large context. A model row in Global Settings can refine this later.
        reasoning: w.reasoning !== false,
        input: ["text", "image"],
        contextWindow: w.context_window || 200000,
        maxTokens: w.max_tokens || 64000,
      });
      registered.push({ provider: pname, model_id: id, display_name: w.display_name || offered.get(id) || id });
    }
  }
  if (registered.length) {
    const tmp = MODELS_JSON + ".tmp";
    fs.writeFileSync(tmp, JSON.stringify(conf, null, 2) + "\n");
    fs.renameSync(tmp, MODELS_JSON);   // atomic: a torn file would break every session
  }
  return { registered, skipped, file: MODELS_JSON };
}
