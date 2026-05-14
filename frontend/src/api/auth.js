import { apiJSON, apiEmpty } from "./client";

const GITHUB_OAUTH_BASE = "https://github.com/login/oauth/authorize";

/**
 * Returns the GitHub OAuth authorization URL.
 * The browser navigates here directly — no backend hop needed for this step.
 * After the user accepts, GitHub redirects to the backend callback, which
 * then redirects to /auth/callback?token=<jwt> on the frontend.
 *
 * @param {boolean} withRepoAccess  Request repo scope for private-repo access.
 * @returns {string}
 */
export function getGitHubOAuthURL(withRepoAccess = false) {
  const params = new URLSearchParams({
    client_id: import.meta.env.VITE_GITHUB_CLIENT_ID,
    scope: withRepoAccess ? "read:user user:email repo" : "read:user user:email",
    state: withRepoAccess ? "repo" : "basic",
  });
  return `${GITHUB_OAUTH_BASE}?${params}`;
}

/**
 * Exchanges the GitHub authorization code for a JWT.
 * Called from the OAuth callback page after GitHub redirects back.
 *
 * GET /auth/github/callback?code=…&state=…
 *
 * @param {string} code   Authorization code from GitHub.
 * @param {string} [state]  "repo" | "basic" (mirrors what the backend sent to GitHub).
 * @returns {Promise<{ access_token: string, token_type: string, user: User }>}
 */
export async function handleGitHubCallback(code, state) {
  const params = new URLSearchParams({ code });
  if (state) params.set("state", state);
  return apiJSON(`/auth/github/callback?${params}`, { method: "GET" });
}

/**
 * Returns the authenticated user's profile.
 * GET /auth/me
 *
 * @returns {Promise<User>}
 */
export async function getMe() {
  return apiJSON("/auth/me");
}

/**
 * Invalidates the current session token on the server.
 * POST /auth/logout  →  204 No Content
 */
export async function logout() {
  return apiEmpty("/auth/logout", { method: "POST" });
}

/**
 * @typedef {Object} User
 * @property {number}      id
 * @property {string}      username
 * @property {string|null} email
 * @property {boolean}     has_repo_access
 * @property {string}      created_at
 */
