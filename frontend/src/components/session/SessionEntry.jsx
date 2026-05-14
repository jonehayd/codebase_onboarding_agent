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
}) {
  const s = STATUS_STYLES[status] ?? STATUS_STYLES.completed;

  return (
    <button
      onClick={onClick}
      title={title}
      className={`
        w-full text-left px-3 py-3 border transition-colors duration-150
        flex flex-col gap-2 cursor-pointer
        ${
          isActive
            ? "bg-surface-raised border-text-subtle"
            : "bg-transparent border-border hover:bg-surface hover:border-text-subtle"
        }
      `}
    >
      {/* title row */}
      <div className="flex items-start justify-between gap-2">
        <span className="text-sm font-medium text-text leading-tight truncate">
          {title}
        </span>

        {/* status badge */}
        <span
          style={{
            color: s.color,
            backgroundColor: `color-mix(in srgb, ${s.color} 10%, transparent)`,
            borderColor: `color-mix(in srgb, ${s.color} 40%, transparent)`,
          }}
          className="shrink-0 inline-flex items-center gap-1.5 px-4 py-0.5 text-xs font-medium border"
        >
          <span
            style={{ backgroundColor: s.color }}
            className="w-1.5 h-1.5 rounded-full"
          />
          {s.label}
        </span>
      </div>

      {/* repo name */}
      <span className="text-xs text-text-subtle font-mono truncate">
        {repoName}
      </span>

      {/* timestamp */}
      <span className="text-xs text-text-subtle">
        Last active {formatTimestamp(lastActive)}
      </span>
    </button>
  );
}
