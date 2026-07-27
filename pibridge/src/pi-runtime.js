// ONE place that knows how to talk to the installed pi runtime, whichever generation
// it is. Everything else in the bridge asks for a runtime and gets the same shape back.
//
// WHY THIS EXISTS: pi 0.81 replaced `AuthStorage` + `ModelRegistry` (synchronous, passed
// separately into createAgentSession) with a single async `ModelRuntime`. The bridge had
// the old pattern hard-wired into nine call sites, so it was pinned to <= 0.80.x - an
// upgrade removed an export and every AI surface died at once. Pinning is not a fix: it
// means never taking a security or model update again. So the version difference lives
// here, and only here.
//
//   pre-0.81 : AuthStorage.create() + ModelRegistry.create(auth, modelsJson)
//              createAgentSession({ authStorage, modelRegistry, ... })
//   0.81+    : await ModelRuntime.create({ modelsPath })
//              createAgentSession({ modelRuntime, ... })
//
// Uniform surface returned by piRuntime():
//   findModel(provider, id) -> model | undefined
//   listModels()            -> [{provider, model_id, display_name, reasoning, context_window}]
//   sessionOpts             -> spread into createAgentSession()
//   loadError()             -> models.json problem, or undefined
//   generation              -> "modelruntime" | "authstorage"  (for logging/diagnostics)
import { MODELS_JSON } from "./models-catalog.js";

// Overridable so the same code can be exercised against another installed copy
// (the update pre-flight probe does exactly this before anything is swapped in).
const PKG = process.env.PI_PKG || "@earendil-works/pi-coding-agent";

let _mod = null;
async function pi() {
  if (!_mod) _mod = await import(PKG);
  return _mod;
}

/** Which generation is installed. Cheap, no side effects. */
export async function piGeneration() {
  const m = await pi();
  if (m.ModelRuntime) return "modelruntime";
  if (m.AuthStorage) return "authstorage";
  return "unknown";
}

// A models.json-FREE view of the installed package, used to answer "does pi know this
// model natively?". Needed because the normal lookup resolves through models.json, so it
// cannot tell a real built-in definition from a stub we wrote there ourselves.
const NO_MODELS_JSON = "/nonexistent/pi-trmm-bridge-no-models.json";
let _builtinRt = null;
async function builtinRuntime() {
  if (_builtinRt !== null) return _builtinRt;
  const m = await pi();
  if (m.ModelRuntime) {
    const rt = await m.ModelRuntime.create({ modelsPath: NO_MODELS_JSON });
    _builtinRt = { get: (p, id) => rt.getModel(p, id) };
  } else if (m.AuthStorage && m.ModelRegistry) {
    const reg = m.ModelRegistry.create(m.AuthStorage.create(), NO_MODELS_JSON);
    _builtinRt = { get: (p, id) => reg.find(p, id) };
  } else {
    _builtinRt = { get: () => undefined };
  }
  return _builtinRt;
}

/** Does the installed package itself define this model (ignoring models.json)? */
export async function builtinModel(provider, id) {
  const rt = await builtinRuntime();
  try { return rt.get(provider, id); } catch { return undefined; }
}

/**
 * Build a runtime with the given provider keys applied as runtime overrides
 * (never persisted to disk - the keys belong to the RMM database).
 * @param {object} keys  { anthropic: "sk-...", openai: "..." }
 */
export async function piRuntime(keys = {}) {
  const m = await pi();

  // ---- 0.81+ : one async ModelRuntime -------------------------------------
  if (m.ModelRuntime) {
    const rt = await m.ModelRuntime.create({ modelsPath: MODELS_JSON });
    for (const [prov, key] of Object.entries(keys)) if (key) rt.setRuntimeApiKey(prov, key);
    return {
      generation: "modelruntime",
      raw: rt,
      findModel: (provider, id) => rt.getModel(provider, id),
      listModels: () => rt.getModels().map(toRow),
      sessionOpts: { modelRuntime: rt },
      loadError: () => (rt.getError ? rt.getError() : undefined),
    };
  }

  // ---- pre-0.81 : AuthStorage + ModelRegistry ------------------------------
  if (m.AuthStorage && m.ModelRegistry) {
    const auth = m.AuthStorage.create();
    for (const [prov, key] of Object.entries(keys)) if (key) auth.setRuntimeApiKey(prov, key);
    // create() (not inMemory()) so models.json is honoured - that is what makes a model
    // the provider has released but this package does not know about runnable.
    const reg = m.ModelRegistry.create(auth, MODELS_JSON);
    return {
      generation: "authstorage",
      raw: reg,
      findModel: (provider, id) => reg.find(provider, id),
      // getAvailable() filters to providers that have a key, which is what every caller
      // here wants (a model with no key is not usable).
      listModels: () => reg.getAvailable().map(toRow),
      sessionOpts: { authStorage: auth, modelRegistry: reg },
      loadError: () => (reg.getError ? reg.getError() : undefined),
    };
  }

  throw new Error(
    `installed pi runtime exposes neither ModelRuntime nor AuthStorage - cannot start ` +
    `(exports seen: ${Object.keys(m).slice(0, 12).join(", ")}...)`,
  );
}

function toRow(x) {
  return {
    provider: x.provider,
    model_id: x.id,
    display_name: x.name || x.id,
    reasoning: !!x.reasoning,
    context_window: x.contextWindow,
  };
}

/**
 * Functional self-test used by the scheduled updater BEFORE a new version is allowed to
 * take over. Deliberately behaviour-based: "can this build a runtime, apply a key and
 * find a model", not "does export X still exist". An export list goes stale; this does not.
 */
export async function piSelfTest(keys = {}) {
  const out = { pkg: PKG };
  try {
    out.generation = await piGeneration();
    const rt = await piRuntime(keys);
    const models = rt.listModels();
    out.models = models.length;
    out.load_error = rt.loadError() || null;
    out.session_opts = Object.keys(rt.sessionOpts);
    // Prove the lookup path used by every surface actually resolves something.
    const first = models[0];
    out.lookup_ok = !!(first && rt.findModel(first.provider, first.model_id));
    out.ok = out.models > 0 && out.lookup_ok && !out.load_error;
    return out;
  } catch (e) {
    out.ok = false;
    out.error = String(e?.message || e);
    return out;
  }
}
