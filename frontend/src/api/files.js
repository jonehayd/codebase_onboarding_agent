import { apiJSON } from "./client";

/**
 * Returns the full list of indexed files for a session.
 * GET /sessions/{session_id}/files
 *
 * @param {number} sessionId
 * @returns {Promise<{ session_id: number, files: FileEntry[] }>}
 */
export async function listFiles(sessionId) {
  return apiJSON(`/sessions/${sessionId}/files`);
}

/**
 * Searches indexed file paths by a query string.
 * GET /sessions/{session_id}/files/search?q=…
 *
 * @param {number} sessionId
 * @param {string} query  Substring to match against file paths.
 * @returns {Promise<{ session_id: number, query: string, files: FileEntry[] }>}
 */
export async function searchFiles(sessionId, query) {
  const params = new URLSearchParams({ q: query });
  return apiJSON(`/sessions/${sessionId}/files/search?${params}`);
}

/**
 * Returns the full source content of a single file.
 * GET /sessions/{session_id}/files/{file_id}
 *
 * @param {number} sessionId
 * @param {number} fileId
 * @returns {Promise<FileContentOut>}
 */
export async function getFileContent(sessionId, fileId) {
  return apiJSON(`/sessions/${sessionId}/files/${fileId}`);
}

/**
 * @typedef {Object} FileEntry
 * @property {number} id
 * @property {string} file_path
 * @property {string} language
 * @property {number} size_bytes
 */

/**
 * @typedef {Object} FileContentOut
 * @property {number} id
 * @property {string} file_path
 * @property {string} language
 * @property {string} content
 */
