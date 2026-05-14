import { useState, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import { LuEllipsis, LuPencil, LuTrash2 } from "react-icons/lu";

const STATUS_STYLES = {
  completed: {
    color: "#22c55e",
    label: "Completed",
  },
  processing: {
    color: "#f59e0b",
    label: "Processing",
  },
  pending: {
    color: "#f59e0b",
    label: "Processing",
  },
  failed: {
    color: "#ef4444",
    label: "Failed",
  },
};

function formatTimestamp(isoString) {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

export default function SessionEntry({
  title = "Untitled Session",
  repoName = "owner/repo",
  status = "completed",
  lastActive = new Date().toISOString(),
  isActive = false,
  onClick,
  onRename,
  onDelete,
}) {
  const s = STATUS_STYLES[status] ?? STATUS_STYLES.processing;

  const [dropdownPos, setDropdownPos] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [isRenaming, setIsRenaming] = useState(false);
  const [renameValue, setRenameValue] = useState(title);
  const menuButtonRef = useRef(null);
  const dropdownRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (isRenaming) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [isRenaming]);

  useEffect(() => {
    if (!dropdownPos) return;
    const handleMouseDown = (e) => {
      if (
        !dropdownRef.current?.contains(e.target) &&
        !menuButtonRef.current?.contains(e.target)
      ) {
        setDropdownPos(null);
      }
    };
    document.addEventListener("mousedown", handleMouseDown);
    return () => document.removeEventListener("mousedown", handleMouseDown);
  }, [dropdownPos]);

  const handleMenuClick = (e) => {
    e.stopPropagation();
    if (dropdownPos) {
      setDropdownPos(null);
      return;
    }
    const rect = menuButtonRef.current.getBoundingClientRect();
    setDropdownPos({ top: rect.bottom + 4, left: rect.left });
  };

  const handleRenameClick = (e) => {
    e.stopPropagation();
    setDropdownPos(null);
    setRenameValue(title);
    setIsRenaming(true);
  };

  const handleDeleteClick = (e) => {
    e.stopPropagation();
    setDropdownPos(null);
    setConfirmDelete(true);
  };

  const handleConfirmDelete = (e) => {
    e.stopPropagation();
    setConfirmDelete(false);
    onDelete?.();
  };

  const commitRename = () => {
    const trimmed = renameValue.trim();
    if (trimmed && trimmed !== title) {
      onRename?.(trimmed);
    }
    setIsRenaming(false);
  };

  const handleRenameKeyDown = (e) => {
    if (e.key === "Enter") commitRename();
    else if (e.key === "Escape") setIsRenaming(false);
  };

  return (
    <>
      <div
        onClick={onClick}
        className={`group w-full text-left px-3 py-3 border transition-colors duration-150
          flex flex-col gap-2 cursor-pointer
          ${
            isActive
              ? "bg-surface-raised border-text-subtle"
              : "bg-transparent border-border hover:bg-surface hover:border-text-subtle"
          }
        `}
      >
        {/* title row */}
        <div className="flex items-center gap-2">
          {isRenaming ? (
            <input
              ref={inputRef}
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              onKeyDown={handleRenameKeyDown}
              onBlur={commitRename}
              onClick={(e) => e.stopPropagation()}
              className="flex-1 min-w-0 text-sm font-medium text-text bg-surface-highest border border-text-subtle px-1 py-0.5 outline-none"
            />
          ) : (
            <span className="flex-1 min-w-0 text-sm font-medium text-text leading-tight truncate">
              {title}
            </span>
          )}

          {/* three-dot menu */}
          <button
            ref={menuButtonRef}
            onClick={handleMenuClick}
            className="shrink-0 p-0.5 opacity-0 group-hover:opacity-100 text-text-muted hover:text-text transition-opacity rounded"
            title="More options"
          >
            <LuEllipsis size={14} />
          </button>
        </div>

        {/* repo name */}
        <span className="text-xs text-text-subtle font-mono truncate">
          {repoName}
        </span>

        {/* bottom row: timestamp + status badge */}
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs text-text-subtle">
            Last active {formatTimestamp(lastActive)}
          </span>

          <span
            style={{
              color: s.color,
              backgroundColor: `color-mix(in srgb, ${s.color} 10%, transparent)`,
              borderColor: `color-mix(in srgb, ${s.color} 40%, transparent)`,
            }}
            className="shrink-0 inline-flex items-center gap-1.5 px-2 py-0.5 text-xs font-medium border"
          >
            <span
              style={{ backgroundColor: s.color }}
              className="w-1.5 h-1.5 rounded-full"
            />
            {s.label}
          </span>
        </div>
      </div>

      {/* Delete confirmation modal */}
      {confirmDelete &&
        createPortal(
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
            onClick={(e) => {
              e.stopPropagation();
              setConfirmDelete(false);
            }}
          >
            <div
              className="bg-surface-raised border border-border w-full max-w-sm mx-4 p-6 flex flex-col gap-4"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex flex-col gap-1">
                <h2 className="text-base font-semibold text-text">
                  Delete session?
                </h2>
                <p className="text-sm text-text-muted">
                  <span className="font-medium text-text">{title}</span> will be
                  permanently deleted. This action cannot be undone.
                </p>
              </div>
              <div className="flex justify-end gap-2">
                <button
                  onClick={() => setConfirmDelete(false)}
                  className="px-4 py-2 text-sm font-medium text-text-muted border border-border hover:text-text hover:border-text-subtle transition-colors cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  onClick={handleConfirmDelete}
                  className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 transition-colors cursor-pointer"
                >
                  Delete
                </button>
              </div>
            </div>
          </div>,
          document.body,
        )}

      {/* fixed-position dropdown — escapes overflow:hidden parents */}
      {dropdownPos && (
        <div
          ref={dropdownRef}
          style={{ top: dropdownPos.top, left: dropdownPos.left }}
          className="fixed z-50 w-36 bg-surface-elevated border border-border shadow-lg py-1"
        >
          <button
            onClick={handleRenameClick}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-text hover:bg-surface-raised transition-colors"
          >
            <LuPencil size={13} />
            Rename
          </button>
          <button
            onClick={handleDeleteClick}
            className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-400 hover:bg-surface-raised transition-colors"
          >
            <LuTrash2 size={13} />
            Delete
          </button>
        </div>
      )}
    </>
  );
}
