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
