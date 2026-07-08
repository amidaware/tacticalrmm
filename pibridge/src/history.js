// Simple per-agent chat history index so the "AI History" device tab can list
// and resume prior conversations. Each agent gets sessions/<agentId>/index.json
// mapping session_id -> { file, name, started, last_activity, model, user }.
import fs from "node:fs";
import path from "node:path";
import { CONFIG } from "./config.js";

function agentDir(agentId) {
  const d = path.join(CONFIG.sessionsRoot, agentId);
  fs.mkdirSync(d, { recursive: true });
  return d;
}

function indexPath(agentId) {
  return path.join(agentDir(agentId), "index.json");
}

export function readIndex(agentId) {
  try {
    return JSON.parse(fs.readFileSync(indexPath(agentId), "utf8"));
  } catch {
    return {};
  }
}

function writeIndex(agentId, idx) {
  fs.writeFileSync(indexPath(agentId), JSON.stringify(idx, null, 2));
}

export function recordSession(agentId, sessionId, info) {
  const idx = readIndex(agentId);
  idx[sessionId] = { ...(idx[sessionId] || {}), ...info };
  writeIndex(agentId, idx);
}

export function touchSession(agentId, sessionId, lastMessage) {
  const idx = readIndex(agentId);
  if (idx[sessionId]) {
    idx[sessionId].last_activity = new Date().toISOString();
    if (lastMessage) idx[sessionId].last_message = lastMessage.slice(0, 200);
    writeIndex(agentId, idx);
  }
}

export function listSessions(agentId) {
  const idx = readIndex(agentId);
  return Object.entries(idx)
    .map(([session_id, v]) => ({ session_id, ...v }))
    .sort((a, b) => (b.last_activity || "").localeCompare(a.last_activity || ""));
}

export function deleteSession(agentId, sessionId) {
  const idx = readIndex(agentId);
  const info = idx[sessionId];
  if (info?.file) {
    try {
      fs.unlinkSync(info.file);
    } catch {}
  }
  delete idx[sessionId];
  writeIndex(agentId, idx);
}
