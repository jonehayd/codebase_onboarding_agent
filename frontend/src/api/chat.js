import { BASE_URL, apiJSON, streamSSE } from "./client";

/**
 * Streams a chat response via Server-Sent Events.
 * POST /sessions/{session_id}/chat
 *
 * The backend emits `data: <token>` lines followed by `data: [DONE]`.
 *
 * @param {number}   sessionId
 * @param {string}   question   User message (1–8000 chars).
 * @param {(chunk: string) => void} onChunk  Called for each streamed token.
 * @param {() => void}             onDone   Called when the stream closes normally.
 * @param {(err: Error) => void}   onError  Called on network or HTTP errors.
 * @returns {() => void}  Abort function — call it to cancel mid-stream.
 */
export function streamChat(sessionId, question, onChunk, onDone, onError) {
  return streamSSE(
    `${BASE_URL}/sessions/${sessionId}/chat`,
    {
      method: "POST",
      body: JSON.stringify({ question }),
    },
    onChunk,
    onDone,
    onError,
  );
}

/**
 * Returns the paginated conversation history for a session.
 * GET /sessions/{session_id}/history
 *
 * @param {number} sessionId
 * @param {{ limit?: number, offset?: number }} [pagination]
 * @returns {Promise<HistoryOut>}
 */
export async function getChatHistory(sessionId, { limit = 50, offset = 0 } = {}) {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  return apiJSON(`/sessions/${sessionId}/history?${params}`);
}

/**
 * @typedef {Object} ChatMessage
 * @property {string} role        "user" | "assistant"
 * @property {string} content
 * @property {string} created_at
 */

/**
 * @typedef {Object} HistoryOut
 * @property {ChatMessage[]} messages
 * @property {number}        total
 * @property {number}        limit
 * @property {number}        offset
 */
