import { VscFolder } from "react-icons/vsc";
import FileTree from "./FileTree";

export default function FileView({
  repoName = "owner/repo",
  files = [],
  selectedId = null,
  onFileClick,
}) {
  return (
    <div className="flex flex-col h-full bg-surface border-r border-border">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-3 border-b border-border shrink-0">
        <VscFolder
          className="text-base shrink-0"
          style={{ color: "#fbbf24" }}
          aria-hidden
        />
        <span className="text-xs font-mono font-medium text-text truncate">
          {repoName}
        </span>
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
