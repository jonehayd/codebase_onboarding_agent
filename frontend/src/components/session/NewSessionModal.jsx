import { useState } from "react";
import { RxCross2 as X } from "react-icons/rx";
import { FaLink } from "react-icons/fa";

export default function NewSessionModal({ isOpen, onClose, onSubmit }) {
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [errors, setErrors] = useState({});

  if (!isOpen) return null;

  function normalizeUrl(value) {
    const v = value.trim();
    if (!v) return v;
    // If it looks like owner/repo (no scheme, no github.com), expand it
    if (!v.startsWith("http://") && !v.startsWith("https://")) {
      return `https://github.com/${v}`;
    }
    return v;
  }

  function validateUrl(value) {
    if (!value.trim()) return "This field cannot be empty";
    const normalized = normalizeUrl(value);
    try {
      const u = new URL(normalized);
      if (!u.hostname.endsWith("github.com"))
        return "URL must point to github.com";
      const parts = u.pathname.replace(/^\/|\/$/, "").split("/");
      if (parts.length !== 2 || !parts[0] || !parts[1])
        return "Expected format: owner/repo";
      return null;
    } catch {
      return "Not a valid URL";
    }
  }

  function handleUrlChange(e) {
    setUrl(e.target.value);
    if (errors.url) setErrors((prev) => ({ ...prev, url: null }));
  }

  function handleSubmit(e) {
    e.preventDefault();
    const urlError = validateUrl(url);
    if (urlError) {
      setErrors({ url: urlError });
      return;
    }
    setErrors({});
    onSubmit?.({ url: normalizeUrl(url), title: title.trim() || null });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      {/* Modal content */}
      <div className="relative bg-surface-raised flex flex-col w-full max-w-lg border border-border p-6 pt-12 mx-4 gap-2">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-text-subtle cursor-pointer hover:text-text transition-colors"
        >
          <X size={20} />
        </button>

        {/* Header */}
        <h2 className="text-text text-2xl">Create New Session</h2>
        <p className="text-sm text-text-subtle mb-6">
          Enter the repository URL and a title for your new session.
        </p>

        {/* Form */}
        <form onSubmit={handleSubmit} className="flex flex-col gap-6">
          {/* Github URL field */}
          <div className="flex flex-col gap-2">
            <label className="text-xs font-semibold text-text tracking-widest uppercase">
              GITHUB URL
            </label>
            <div
              className={`flex items-center border p-2 gap-2 focus-within:border-text-subtle transition-colors ${errors.url ? "border-red-500" : "border-border"}`}
            >
              <input
                type="text"
                value={url}
                onChange={handleUrlChange}
                placeholder="https://github.com/owner/repo or owner/repo"
                className="flex-1 text-text placeholder-placeholder outline-none font-mono bg-transparent"
              />
              <FaLink className="text-text-subtle shrink-0" />
            </div>
            {errors.url && (
              <span className="text-xs text-red-500">{errors.url}</span>
            )}
          </div>

          {/* Optional title field */}
          <div className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-text tracking-widest uppercase">
                Session Title
              </label>
              <span className="text-xs text-text-subtle uppercase tracking-widest">
                Optional
              </span>
            </div>
            <div className="flex items-center border border-border bg-surface-raised px-3 py-2 focus-within:border-text-subtle transition-colors">
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Auth flow for repository XYZ"
                className="flex-1 text-text placeholder-placeholder outline-none font-mono bg-transparent"
              />
            </div>
          </div>

          {/* submit button */}
          <button
            type="submit"
            className="w-full py-3 bg-text text-black font-semibold text-sm tracking-widest uppercase cursor-pointer hover:bg-text-muted transition-colors duration-150 mt-1"
          >
            Create Session
          </button>
        </form>
      </div>
    </div>
  );
}
