// Thin fetch wrapper for the INFERNO API. All calls carry the session cookie.

async function req(method, path, body) {
  const opts = {
    method,
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
  };
  if (body !== undefined) opts.body = JSON.stringify(body);

  let res;
  try {
    res = await fetch(path, opts);
  } catch (e) {
    throw { status: 0, error: "NETWORK ERROR — the terminal is unreachable." };
  }

  let data = null;
  try {
    data = await res.json();
  } catch (e) {
    /* empty / non-JSON body */
  }

  if (!res.ok) {
    const fallback =
      res.status === 429
        ? "Too many requests — slow down and try again in a moment."
        : res.status === 413
        ? "Command too long."
        : `Request failed (HTTP ${res.status}).`;
    throw { status: res.status, error: (data && data.error) || fallback };
  }
  return data;
}

export const getState = () => req("GET", "/api/state");
export const auth = (passphrase) => req("POST", "/api/auth", { passphrase });
export const logout = () => req("POST", "/api/logout");
export const getCircle = (n) => req("GET", `/api/circle/${n}`);
export const chat = (message, level) => req("POST", "/api/chat", { message, level });
export const submitPassphrase = (passphrase, circle) =>
  req("POST", "/api/passphrase", { passphrase, circle });
export const openVault = (key, level) => req("POST", "/api/vault", { key, level });
export const resetCircle = (level) => req("POST", "/api/reset-circle", { level });
export const restart = () => req("POST", "/api/restart");
