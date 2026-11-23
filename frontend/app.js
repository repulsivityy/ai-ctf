import * as api from "/api.js";
import { renderAscentMap } from "/ascent-map.js";

const $ = (sel) => document.querySelector(sel);
const md = (text) =>
  (window.marked ? window.marked.parse(String(text || "")) : escapeHtml(text));

function escapeHtml(s) {
  return String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;",
  }[c]));
}

let STATE = null; // last /api/state payload
let viewCircle = 1; // circle the main pane is showing (this tab), not the cookie's "current"

// --------------------------------------------------------------------------- //
// Boot
// --------------------------------------------------------------------------- //
async function boot() {
  let state;
  try {
    state = await api.getState();
  } catch (e) {
    state = { authenticated: false };
  }
  if (!state.authenticated) {
    showGateway();
    return;
  }
  STATE = state;
  $("#gateway").hidden = true;
  $("#terminal").hidden = false;
  renderShell(state);
  await loadCircle(state.current_level);
}

// --------------------------------------------------------------------------- //
// Gateway
// --------------------------------------------------------------------------- //
function showGateway() {
  $("#terminal").hidden = true;
  $("#gateway").hidden = false;
  $("#gate-input").focus();
}

$("#gate-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const err = $("#gate-error");
  err.hidden = true;
  const val = $("#gate-input").value;
  try {
    const res = await api.auth(val);
    $("#gate-input").value = "";
    // Confirm the session cookie actually round-trips before entering — a
    // silent bounce back to this screen otherwise looks like a wrong password.
    let check;
    try {
      check = await api.getState();
    } catch (_) {
      check = res && res.state ? res.state : { authenticated: false };
    }
    if (!check.authenticated) {
      err.textContent =
        "Passphrase accepted, but the session cookie did not stick. Enable cookies for this site (or disable a blocker) and retry.";
      err.hidden = false;
      return;
    }
    STATE = check;
    $("#gateway").hidden = true;
    $("#terminal").hidden = false;
    renderShell(check);
    await loadCircle(check.current_level);
  } catch (ex) {
    err.textContent = ex.error || "ACCESS DENIED. Authentication Failure.";
    err.hidden = false;
  }
});

$("#logout").addEventListener("click", async () => {
  try { await api.logout(); } catch (e) { /* ignore */ }
  location.reload();
});

// --------------------------------------------------------------------------- //
// Sidebar shell
// --------------------------------------------------------------------------- //
// Number of playable circles, from /api/state. Fallback: count built strata.
function maxPlayable(state) {
  if (Number.isInteger(state.max_playable)) return state.max_playable;
  return (state.circles || []).filter((c) => c.status !== "void").length;
}

function renderShell(state) {
  STATE = state;
  const total = maxPlayable(state);
  const cur = state.circles.find((c) => c.n === viewCircle);
  $("#briefing").textContent = cur ? cur.briefing : "";

  // Ascent map
  try {
    renderAscentMap($("#ascent-map"), {
      strata: state.circles,
      cleared: state.cleared || 0,
      total,
      exitOpen: state.exit_open,
      onSelect: (n) => loadCircle(n),
    });
  } catch (e) {
    console.error("ascent map failed", e);
    $("#ascent-map").innerHTML =
      '<p class="am-fallback">Ascent Map unavailable — use manual override below.</p>';
  }

  // Ascent gate — for the circle THIS tab is viewing
  const next = viewCircle + 1;
  const gateVisible = viewCircle < total && !state.unlocked_levels.includes(next);
  $("#gate").hidden = !gateVisible;
  if (gateVisible) {
    $("#gate-block-label").textContent =
      `Enter the Exit Passphrase to unlock Circle ${next}:`;
    if ($("#gate").dataset.next !== String(next)) {
      // only wipe the field / message when the target circle actually changed
      $("#gate").dataset.next = String(next);
      $("#gate-pass").value = "";
      $("#gate-msg").hidden = true;
    }
  } else {
    $("#gate").dataset.next = "";
  }

  // Vault Console — only on circles whose fragment hoards a vault key
  const vaultVisible = !!(cur && cur.has_vault);
  $("#vault").hidden = !vaultVisible;
  if ($("#vault").dataset.circle !== String(vaultVisible ? viewCircle : "")) {
    // circle changed: clear the field and any previous result
    $("#vault").dataset.circle = vaultVisible ? String(viewCircle) : "";
    $("#vault-key").value = "";
    $("#vault-msg").hidden = true;
    $("#vault-msg").replaceChildren();
  }

  // Manual-override select
  const mo = $("#manual-override");
  if (state.unlocked_levels.length > 1) {
    mo.hidden = false;
    const sel = $("#mo-select");
    sel.innerHTML = state.unlocked_levels
      .map((n) => `<option value="${n}">Circle ${n}</option>`)
      .join("");
    sel.value = String(state.current_level);
  } else {
    mo.hidden = true;
  }
}

$("#mo-select").addEventListener("change", (e) => loadCircle(Number(e.target.value)));

// --------------------------------------------------------------------------- //
// Circle load + transcript
// --------------------------------------------------------------------------- //
async function loadCircle(n) {
  let circle;
  try {
    circle = await api.getCircle(n);
  } catch (ex) {
    appendRow("error", ex.error || "CONNECTION ERROR");
    return;
  }
  viewCircle = n;
  $("#circle-title").textContent = circle.title;
  $("#circle-subtitle").textContent = circle.subtitle;

  const t = $("#transcript");
  t.innerHTML = "";
  circle.transcript.forEach((m) => {
    if (m.role === "system_log") appendRow("system_log", m.text);
    else appendRow(m.role, m.text);
  });
  scrollTranscript();

  // refresh sidebar state (current_level changed server-side)
  try {
    STATE = await api.getState();
    renderShell(STATE);
  } catch (e) { /* keep old shell */ }
}

function appendRow(kind, text, opts = {}) {
  const t = $("#transcript");
  const row = document.createElement("div");
  row.className = `row row--${kind}`;
  if (kind === "system_log") {
    row.textContent = `⚡ [SYSTEM LOG: ${text} CALLED]`;
  } else if (kind === "error") {
    row.textContent = text;
  } else if (kind === "user") {
    row.textContent = text;
  } else {
    // assistant
    row.innerHTML = md(text);
    if (opts.dlp) row.classList.add("row--dlp");
  }
  t.appendChild(row);
  return row;
}

function scrollTranscript() {
  const t = $("#transcript");
  t.scrollTop = t.scrollHeight;
}

// --------------------------------------------------------------------------- //
// Composer
// --------------------------------------------------------------------------- //
const input = $("#composer-input");
input.addEventListener("input", () => {
  input.style.height = "auto";
  input.style.height = Math.min(input.scrollHeight, 160) + "px";
});
input.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    $("#composer").requestSubmit();
  }
});

$("#composer").addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = input.value.trim();
  if (!message) return;

  const circle = viewCircle;
  appendRow("user", message);
  input.value = "";
  input.style.height = "auto";
  scrollTranscript();
  setComposerEnabled(false);

  const pending = appendRow("assistant", "");
  pending.classList.add("row--pending");
  pending.textContent = "· establishing link ·";
  scrollTranscript();

  try {
    const res = await api.chat(message, circle);
    pending.remove();
    (res.system_logs || []).forEach((c) => appendRow("system_log", c.name.toUpperCase()));
    appendRow("assistant", res.reply, { dlp: res.dlp_triggered });
  } catch (ex) {
    pending.remove();
    appendRow("error", ex.error || "TERMINAL ERROR");
  } finally {
    setComposerEnabled(true);
    scrollTranscript();
    // A successful chat may have unlocked nothing, but refresh anyway (cheap).
    try {
      STATE = await api.getState();
      renderShell(STATE);
    } catch (e) { /* ignore */ }
  }
});

function setComposerEnabled(on) {
  input.disabled = !on;
  $("#composer-send").disabled = !on;
  if (on) input.focus();
}

// --------------------------------------------------------------------------- //
// Ascent gate
// --------------------------------------------------------------------------- //
$("#gate-submit").addEventListener("click", submitGate);
$("#gate-pass").addEventListener("keydown", (e) => {
  if (e.key === "Enter") { e.preventDefault(); submitGate(); }
});

async function submitGate() {
  const msg = $("#gate-msg");
  const val = $("#gate-pass").value;
  try {
    const res = await api.submitPassphrase(val, viewCircle);
    if (res.ok) {
      msg.textContent = `ACCESS GRANTED. Circle ${res.unlocked} unlocked.`;
      msg.className = "gate-msg ok";
      msg.hidden = false;
      STATE = res.state;
      renderShell(STATE);
      await loadCircle(res.unlocked);
    } else {
      msg.textContent = res.error || "ACCESS DENIED. Incorrect Exit Passphrase.";
      msg.className = "gate-msg err";
      msg.hidden = false;
    }
  } catch (ex) {
    msg.textContent = ex.error || "ACCESS DENIED. Incorrect Exit Passphrase.";
    msg.className = "gate-msg err";
    msg.hidden = false;
  }
}

// --------------------------------------------------------------------------- //
// Vault Console
// --------------------------------------------------------------------------- //
$("#vault-submit").addEventListener("click", submitVault);
$("#vault-key").addEventListener("keydown", (e) => {
  if (e.key === "Enter") { e.preventDefault(); submitVault(); }
});

async function submitVault() {
  const msg = $("#vault-msg");
  const val = $("#vault-key").value;
  const btn = $("#vault-submit");
  btn.disabled = true;
  msg.replaceChildren();
  try {
    const res = await api.openVault(val, viewCircle);
    if (res.ok) {
      // textContent only — never inject server data as HTML
      const head = document.createElement("span");
      head.textContent = "VAULT OPEN. Exit Passphrase:";
      const pass = document.createElement("code");
      pass.className = "vault-passphrase";
      pass.textContent = res.passphrase;
      msg.append(head, pass);
      msg.className = "gate-msg ok";
    } else {
      msg.textContent = res.error || "VAULT DENIED. Invalid key.";
      msg.className = "gate-msg err";
    }
  } catch (ex) {
    msg.textContent = ex.error || "VAULT DENIED. Invalid key.";
    msg.className = "gate-msg err";
  } finally {
    msg.hidden = false;
    btn.disabled = false;
  }
}

// --------------------------------------------------------------------------- //
// Reset / Restart
// --------------------------------------------------------------------------- //
$("#reset-circle").addEventListener("click", async () => {
  try {
    await api.resetCircle(viewCircle);
    await loadCircle(viewCircle);
  } catch (ex) {
    appendRow("error", ex.error || "TERMINAL ERROR");
  }
});

$("#restart").addEventListener("click", () => {
  $("#restart-confirm").hidden = false;
});
$("#restart-no").addEventListener("click", () => {
  $("#restart-confirm").hidden = true;
});
$("#restart-yes").addEventListener("click", async () => {
  $("#restart-confirm").hidden = true;
  try {
    const res = await api.restart();
    STATE = res.state;
    renderShell(STATE);
    await loadCircle(1);
  } catch (ex) {
    appendRow("error", ex.error || "TERMINAL ERROR");
  }
});

boot();
