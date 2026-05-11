import { LuChevronsLeft } from "react-icons/lu";
import { VscFolder } from "react-icons/vsc";
import FileTree from "./FileTree";

export default function FileView({
  repoName = "owner/repo",
  files = [],
  selectedId = null,
  onFileClick,
  onToggle,
}) {
  return (
    <div className="flex flex-col h-full bg-surface-raised border-r border-border">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-3 border-b border-border shrink-0">
        <VscFolder
          className="text-base shrink-0"
          style={{ color: "#fbbf24" }}
          aria-hidden
        />
        <span className="text-xs font-mono font-medium text-text truncate flex-1">
          {repoName}
        </span>
        {onToggle && (
          <button
            onClick={onToggle}
            className="p-1 rounded text-text-muted hover:text-text hover:bg-surface-high transition-colors shrink-0"
            title="Collapse file tree"
          >
            <LuChevronsLeft size={14} />
          </button>
        )}
      </div>

      {/* Tree */}
      <div className="flex-1 overflow-y-auto">
        <FileTree
          files={files}
          selectedId={selectedId}
          onFileClick={onFileClick}
        />
      </div>
    </div>
  );
}
