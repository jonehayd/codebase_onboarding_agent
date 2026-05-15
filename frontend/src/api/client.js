export const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export function getAuthHeaders() {
  const token = localStorage.getItem("token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

// Resolves with the raw Response, or throws an Error with the server message.
export async function apiFetch(path, { headers, ...options } = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { ...getAuthHeaders(), ...headers },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    let message;
    try {
      message = JSON.parse(text)?.detail ?? text;
    } catch {
      message = text;
    }
    throw new Error(message || `HTTP ${res.status}`);
  }
  return res;
}

// Convenience: resolves with parsed JSON body.
export async function apiJSON(path, options = {}) {
  const res = await apiFetch(path, options);
  return res.json();
}

// Convenience: resolves with no value (for 204 responses).
export async function apiEmpty(path, options = {}) {
  await apiFetch(path, options);
}

/**
 * Consumes a Server-Sent Events stream returned by the backend chat endpoints.
 *
 * @param {string} url           Full URL (including BASE_URL).
 * @param {RequestInit} options  fetch options (method, headers, body, …).
 * @param {(chunk: string) => void} onChunk  Called for each text token.
 * @param {() => void}           onDone   Called when the stream ends normally.
 * @param {(err: Error) => void} onError  Called on network or HTTP errors.
 * @returns {() => void}  Abort function — call it to cancel mid-stream.
 */
export function streamSSE(url, options, onChunk, onDone, onError) {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers: { ...getAuthHeaders(), ...options?.headers },
      });

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop(); // keep any incomplete trailing line

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data = line.slice(6);
          if (data === "[DONE]") {
            onDone?.();
            return;
          }
          let chunk;
          try {
            chunk = JSON.parse(data);
          } catch {
            chunk = data;
          }
          onChunk?.(chunk);
        }
      }

      onDone?.();
    } catch (err) {
      if (err.name !== "AbortError") onError?.(err);
    }
  })();

  return () => controller.abort();
}
