#!/usr/bin/env node
/**
 * suggest-compact.js
 * PreToolUse hook that tracks tool invocations and suggests /compact at logical thresholds.
 *
 * Setup in ~/.claude/settings.json:
 * {
 *   "hooks": {
 *     "PreToolUse": [
 *       { "matcher": "Edit",  "hooks": [{ "type": "command", "command": "node ~/.claude/skills/strategic-compact/suggest-compact.js" }] },
 *       { "matcher": "Write", "hooks": [{ "type": "command", "command": "node ~/.claude/skills/strategic-compact/suggest-compact.js" }] }
 *     ]
 *   }
 * }
 *
 * Env vars:
 *   COMPACT_THRESHOLD  — tool calls before first suggestion (default: 50)
 */

const fs = require('fs');
const os = require('os');
const path = require('path');

const COUNTER_FILE = path.join(os.tmpdir(), 'claude-tool-count.json');
const THRESHOLD = parseInt(process.env.COMPACT_THRESHOLD || '50', 10);
const REMINDER_INTERVAL = 25;

// Load or initialise counter
let state = { count: 0, sessionStart: Date.now() };
try {
  const raw = fs.readFileSync(COUNTER_FILE, 'utf8');
  const parsed = JSON.parse(raw);
  // Reset counter if it's from a different day (new session heuristic)
  const ageHours = (Date.now() - (parsed.sessionStart || 0)) / 36e5;
  if (ageHours < 24) state = parsed;
} catch (_) { /* first run */ }

state.count += 1;

// Persist updated count
try {
  fs.writeFileSync(COUNTER_FILE, JSON.stringify(state), 'utf8');
} catch (_) { /* ignore write errors */ }

// Decide whether to suggest compaction
const shouldSuggest =
  state.count === THRESHOLD ||
  (state.count > THRESHOLD && (state.count - THRESHOLD) % REMINDER_INTERVAL === 0);

if (shouldSuggest) {
  const extra = state.count > THRESHOLD
    ? ` (${state.count - THRESHOLD} calls past threshold)`
    : '';
  process.stderr.write(
    `\n💡 [strategic-compact] ${state.count} tool calls this session${extra}.\n` +
    `   Consider running /compact at this logical boundary.\n` +
    `   Tip: /compact Focus on the next task you want to tackle\n\n`
  );
}
