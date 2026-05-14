import { BASE_URL, apiJSON, streamSSE } from "./client";

/**
 * Returns public repository info for a share link — no auth required.
 * GET /share/{token}
 *
 * @param {string} token  Share link token.
 * @returns {Promise<ShareInfoOut>}
 */
export async function getSharedRepo(token) {
  return apiJSON(`/share/${token}`, { headers: {} });
}

/**
 * Returns conversation history for a shared session — no auth required.
 * GET /share/{token}/history
 *
 * @param {string} token
 * @returns {Promise<{ messages: Array, total: number }>}
 */
export async function getSharedHistory(token, { limit = 50, offset = 0 } = {}) {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  return apiJSON(`/share/${token}/history?${params}`, { headers: {} });
}

/**
 * Returns the indexed files for a shared session's repo — no auth required.
 * GET /share/{token}/files
 *
 * @param {string} token
 * @returns {Promise<{ session_id: number, files: FileEntry[] }>}
 */
export async function listSharedFiles(token) {
  return apiJSON(`/share/${token}/files`, { headers: {} });
}

/**
 * Fetches the source content of a single file via share link — no auth required.
 * GET /share/{token}/files/{file_id}
 *
 * @param {string} token
 * @param {number} fileId
 * @returns {Promise<{ id: number, file_path: string, language: string, content: string }>}
 */
export async function getSharedFileContent(token, fileId) {
  return apiJSON(`/share/${token}/files/${fileId}`, { headers: {} });
}

/**
 * Streams a chat response via a public share link — no auth required.
 * POST /share/{token}/chat
 *
 * @param {string}   token      Share link token.
 * @param {string}   question   User message (1–8000 chars).
 * @param {(chunk: string) => void} onChunk
 * @param {() => void}             onDone
 * @param {(err: Error) => void}   onError
 * @returns {() => void}  Abort function.
 */
export function streamSharedChat(token, question, onChunk, onDone, onError) {
  return streamSSE(
    `${BASE_URL}/share/${token}/chat`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    },
    onChunk,
    onDone,
    onError,
  );
}

/**
 * @typedef {Object} ShareInfoOut
 * @property {number} session_id
 * @property {number} repo_id
 * @property {string} owner
 * @property {string} name
 * @property {string} url
 * @property {string} status
 */
