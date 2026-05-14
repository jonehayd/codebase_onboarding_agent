import { apiJSON, apiEmpty } from "./client";

// ── Session CRUD ────────────────────────────────────────────────────────────

/**
 * Creates a new session and kicks off repository ingestion.
 * POST /sessions?url=…&title=…  →  201 Created
 *
 * @param {string}      url    GitHub repository URL.
 * @param {string|null} title  Optional session title (max 500 chars).
 * @returns {Promise<CreateSessionOut>}
 */
export async function createSession(url, title = null) {
  const params = new URLSearchParams({ url });
  if (title) params.set("title", title);
  return apiJSON(`/sessions?${params}`, { method: "POST" });
}

/**
 * Returns all sessions belonging to the authenticated user.
 * GET /sessions
 *
 * @returns {Promise<{ sessions: SessionSummary[] }>}
 */
export async function listSessions() {
  return apiJSON("/sessions");
}

/**
 * Returns full details for a single session including its repository info.
 * GET /sessions/{session_id}
 *
 * @param {number} sessionId
 * @returns {Promise<SessionDetail>}
 */
export async function getSession(sessionId) {
  return apiJSON(`/sessions/${sessionId}`);
}

/**
 * Renames a session.
 * PATCH /sessions/{session_id}
 *
 * @param {number} sessionId
 * @param {string} title  New title (1–500 chars).
 * @returns {Promise<{ session_id: number, title: string }>}
 */
export async function updateSession(sessionId, title) {
  return apiJSON(`/sessions/${sessionId}`, {
    method: "PATCH",
    body: JSON.stringify({ title }),
  });
}

/**
 * Permanently deletes a session and its data.
 * DELETE /sessions/{session_id}  →  204 No Content
 *
 * @param {number} sessionId
 */
export async function deleteSession(sessionId) {
  return apiEmpty(`/sessions/${sessionId}`, { method: "DELETE" });
}

// ── Ingestion status & control ──────────────────────────────────────────────

/**
 * Returns the current ingestion status, progress, and statistics.
 * GET /sessions/{session_id}/status
 *
 * @param {number} sessionId
 * @returns {Promise<SessionStatusOut>}
 */
export async function getSessionStatus(sessionId) {
  return apiJSON(`/sessions/${sessionId}/status`);
}

/**
 * Requests cancellation of an in-progress ingestion job.
 * POST /sessions/{session_id}/cancel
 *
 * @param {number} sessionId
 * @returns {Promise<{ detail: string }>}
 */
export async function cancelIngestion(sessionId) {
  return apiJSON(`/sessions/${sessionId}/cancel`, { method: "POST" });
}

/**
 * Checks whether the indexed commit is behind the repository's latest commit.
 * GET /sessions/{session_id}/freshness
 *
 * @param {number} sessionId
 * @returns {Promise<{ is_stale: boolean, stored_commit: string|null, latest_commit: string }>}
 */
export async function checkFreshness(sessionId) {
  return apiJSON(`/sessions/${sessionId}/freshness`);
}

/**
 * Triggers a full re-ingestion of the repository.
 * POST /sessions/{session_id}/reingest  →  202 Accepted
 *
 * @param {number} sessionId
 * @returns {Promise<{ session_id: number, repo_id: number, status: string }>}
 */
export async function reingestSession(sessionId) {
  return apiJSON(`/sessions/${sessionId}/reingest`, { method: "POST" });
}

// ── Share links ─────────────────────────────────────────────────────────────

/**
 * Creates (or replaces) a public share link for a session.
 * POST /sessions/{session_id}/share
 *
 * @param {number} sessionId
 * @returns {Promise<{ token: string, url: string }>}
 */
export async function createShareLink(sessionId) {
  return apiJSON(`/sessions/${sessionId}/share`, { method: "POST" });
}

/**
 * Revokes the share link for a session.
 * DELETE /sessions/{session_id}/share  →  204 No Content
 *
 * @param {number} sessionId
 */
export async function revokeShareLink(sessionId) {
  return apiEmpty(`/sessions/${sessionId}/share`, { method: "DELETE" });
}

// ── JSDoc types ─────────────────────────────────────────────────────────────

/**
 * @typedef {Object} CreateSessionOut
 * @property {number} session_id
 * @property {number} repo_id
 * @property {string} owner
 * @property {string} name
 * @property {string} status
 * @property {string} created_at
 */

/**
 * @typedef {Object} SessionSummary
 * @property {number}      session_id
 * @property {string|null} title
 * @property {number}      repo_id
 * @property {string}      owner
 * @property {string}      name
 * @property {string}      url
 * @property {string}      status
 * @property {string}      created_at
 * @property {string}      last_active_at
 */

/**
 * @typedef {Object} SessionDetail
 * @property {number}      session_id
 * @property {string|null} title
 * @property {string}      created_at
 * @property {string}      last_active_at
 * @property {RepoDetail}  repo
 */

/**
 * @typedef {Object} RepoDetail
 * @property {number}      id
 * @property {string}      owner
 * @property {string}      name
 * @property {string}      url
 * @property {string}      status
 * @property {string|null} commit_hash
 * @property {string}      created_at
 * @property {number}      file_count
 * @property {number}      chunk_count
 */

/**
 * @typedef {Object} SessionStatusOut
 * @property {number}      session_id
 * @property {number}      repo_id
 * @property {string}      status
 * @property {string}      stage
 * @property {number}      percent
 * @property {number}      files_total
 * @property {number}      file_count
 * @property {number}      vector_count
 * @property {number|null} elapsed_seconds
 * @property {string|null} commit_hash
 */
