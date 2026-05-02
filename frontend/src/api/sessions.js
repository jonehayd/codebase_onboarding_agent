const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

function authHeaders() {
  const token = localStorage.getItem("token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export async function getSessionDetail(sessionId) {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function getSessionStatus(sessionId) {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/status`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function cancelIngestion(sessionId) {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/cancel`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function retryIngestion(sessionId) {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/reingest`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function createSession(url, title) {
  const params = new URLSearchParams({ url });
  if (title) params.set("title", title);
  const res = await fetch(`${BASE_URL}/sessions?${params}`, {
    method: "POST",
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function listSessions() {
  const res = await fetch(`${BASE_URL}/sessions`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
