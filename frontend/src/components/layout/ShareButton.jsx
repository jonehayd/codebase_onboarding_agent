import { useState, useRef, useEffect } from "react";
import { LuShare2, LuCopy, LuCheck, LuTrash2, LuX } from "react-icons/lu";
import { createShareLink, revokeShareLink } from "@/api/sessions";

/**
 * Share button shown in the header when a completed session is active.
 *
 * @param {{ activeSession: { id: number, status: string } | null }} props
 */
export default function ShareButton({ activeSession }) {
  const [open, setOpen] = useState(false);
  const [shareUrl, setShareUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState(null);
  const popoverRef = useRef(null);
  const prevSessionId = useRef(null);

  // Reset state whenever the active session changes
  useEffect(() => {
    if (activeSession?.id !== prevSessionId.current) {
      prevSessionId.current = activeSession?.id ?? null;
      setShareUrl(null);
      setOpen(false);
      setError(null);
    }
  }, [activeSession?.id]);

  // Close popover on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  if (!activeSession || activeSession.status !== "completed") return null;

  const handleOpen = async () => {
    if (open) {
      setOpen(false);
      return;
    }
    setOpen(true);

    if (!shareUrl) {
      setLoading(true);
      setError(null);
      try {
        const data = await createShareLink(activeSession.id);
        setShareUrl(data.url);
      } catch (err) {
        setError(err.message ?? "Failed to create share link");
      } finally {
        setLoading(false);
      }
    }
  };

  const handleCopy = async () => {
    if (!shareUrl) return;
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback for browsers that block clipboard API
      const el = document.createElement("textarea");
      el.value = shareUrl;
      document.body.appendChild(el);
      el.select();
      document.execCommand("copy");
      document.body.removeChild(el);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleRevoke = async () => {
    setLoading(true);
    setError(null);
    try {
      await revokeShareLink(activeSession.id);
      setShareUrl(null);
      setOpen(false);
    } catch (err) {
      setError(err.message ?? "Failed to revoke link");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative" ref={popoverRef}>
      <button
        onClick={handleOpen}
        title="Share session"
        className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-text-muted hover:text-text transition-colors duration-150 cursor-pointer rounded"
      >
        <LuShare2 size={15} />
        <span>Share</span>
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-2 w-80 bg-surface-elevated border border-border rounded shadow-lg z-50 p-4">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-medium text-text">Share session</span>
            <button
              onClick={() => setOpen(false)}
              className="text-text-subtle hover:text-text cursor-pointer"
            >
              <LuX size={14} />
            </button>
          </div>

          {loading && (
            <p className="text-xs text-text-muted">Generating link…</p>
          )}

          {error && <p className="text-xs text-error">{error}</p>}

          {shareUrl && !loading && (
            <>
              <p className="text-xs text-text-subtle mb-2">
                Anyone with this link can view this session and ask questions.
              </p>
              <div className="flex items-center gap-2 bg-surface-raised border border-border rounded px-2 py-1.5 mb-3">
                <span className="flex-1 text-xs text-text-muted truncate font-mono">
                  {shareUrl}
                </span>
                <button
                  onClick={handleCopy}
                  className="shrink-0 text-text-subtle hover:text-text transition-colors cursor-pointer"
                  title="Copy link"
                >
                  {copied ? (
                    <LuCheck size={13} className="text-success" />
                  ) : (
                    <LuCopy size={13} />
                  )}
                </button>
              </div>
              <button
                onClick={handleRevoke}
                disabled={loading}
                className="flex items-center gap-1.5 text-xs text-error hover:text-error/80 transition-colors cursor-pointer disabled:opacity-50"
              >
                <LuTrash2 size={12} />
                Revoke link
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
