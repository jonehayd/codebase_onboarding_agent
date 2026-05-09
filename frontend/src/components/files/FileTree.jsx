import { useState } from "react";
import {
  VscFolder,
  VscFolderOpened,
  VscFile,
  VscJson,
  VscMarkdown,
  VscChevronRight,
  VscChevronDown,
  VscSymbolColor,
} from "react-icons/vsc";
import { SiPython, SiJavascript, SiTypescript, SiHtml5 } from "react-icons/si";
import { cn } from "@/lib/utils";

// --- File icon map by extension ---

const FILE_ICONS = {
  py: { Icon: SiPython, color: "#60a5fa" },
  js: { Icon: SiJavascript, color: "#fbbf24" },
  jsx: { Icon: SiJavascript, color: "#fbbf24" },
  mjs: { Icon: SiJavascript, color: "#fbbf24" },
  cjs: { Icon: SiJavascript, color: "#fbbf24" },
  ts: { Icon: SiTypescript, color: "#60a5fa" },
  tsx: { Icon: SiTypescript, color: "#60a5fa" },
  html: { Icon: SiHtml5, color: "#f97316" },
  css: { Icon: VscSymbolColor, color: "#60a5fa" },
  scss: { Icon: VscSymbolColor, color: "#e879f9" },
  sass: { Icon: VscSymbolColor, color: "#e879f9" },
  json: { Icon: VscJson, color: "#fbbf24" },
  md: { Icon: VscMarkdown, color: "#a1a1aa" },
  mdx: { Icon: VscMarkdown, color: "#a1a1aa" },
};

const FOLDER_COLOR = "#fbbf24";
const DEFAULT_FILE = { Icon: VscFile, color: "#71717a" };

function getFileIcon(filename) {
  const ext = filename.split(".").pop()?.toLowerCase() ?? "";
  return FILE_ICONS[ext] ?? DEFAULT_FILE;
}

// --- Tree builder ---
// Converts a flat files array into a nested map of FolderNode / FileLeaf objects.

function buildTree(files) {
  const root = {};
  for (const file of files) {
    const parts = file.file_path.split("/");
    let node = root;
    for (let i = 0; i < parts.length - 1; i++) {
      const part = parts[i];
      if (!node[part]) {
        node[part] = { _type: "folder", name: part, children: {} };
      }
      node = node[part].children;
    }
    const fileName = parts[parts.length - 1];
    node[fileName] = { _type: "file", name: fileName, ...file };
  }
  return root;
}

// Folders first (a-z), then files (a-z)
function sortedEntries(nodeMap) {
  const entries = Object.values(nodeMap);
  const folders = entries
    .filter((n) => n._type === "folder")
    .sort((a, b) => a.name.localeCompare(b.name));
  const files = entries
    .filter((n) => n._type === "file")
    .sort((a, b) => a.name.localeCompare(b.name));
  return [...folders, ...files];
}

// --- FileNode ---

function FileNode({ file, depth, selectedId, onFileClick }) {
  const { Icon, color } = getFileIcon(file.name);
  const isSelected = file.id === selectedId;

  return (
    <button
      onClick={() => onFileClick?.(file)}
      title={file.file_path}
      className={cn(
        "w-full flex items-center gap-2 py-1 text-left text-xs font-mono truncate",
        "border-l-2 transition-colors duration-100 cursor-pointer",
        isSelected
          ? "bg-surface-raised text-text border-text"
          : "text-text-muted border-transparent hover:bg-surface hover:text-text",
      )}
      style={{ paddingLeft: `${depth * 16 + 8}px` }}
    >
      <Icon style={{ color }} className="shrink-0 text-sm" aria-hidden />
      <span className="truncate">{file.name}</span>
    </button>
  );
}

// --- FolderNode ---

function FolderNode({
  name,
  node,
  depth,
  selectedId,
  onFileClick,
  defaultOpen = false,
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const children = sortedEntries(node.children);

  return (
    <div>
      <button
        onClick={() => setIsOpen((v) => !v)}
        className="w-full flex items-center gap-2 py-1 text-left text-xs font-mono
          text-text-subtle hover:text-text hover:bg-surface
          transition-colors duration-100 cursor-pointer"
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        {isOpen ? (
          <VscChevronDown
            className="shrink-0 text-xs text-text-subtle"
            aria-hidden
          />
        ) : (
          <VscChevronRight
            className="shrink-0 text-xs text-text-subtle"
            aria-hidden
          />
        )}
        {isOpen ? (
          <VscFolderOpened
            style={{ color: FOLDER_COLOR }}
            className="shrink-0 text-sm"
            aria-hidden
          />
        ) : (
          <VscFolder
            style={{ color: FOLDER_COLOR }}
            className="shrink-0 text-sm"
            aria-hidden
          />
        )}
        <span className="truncate">{name}</span>
      </button>

      {isOpen && (
        <div>
          {children.map((child) =>
            child._type === "folder" ? (
              <FolderNode
                key={child.name}
                name={child.name}
                node={child}
                depth={depth + 1}
                selectedId={selectedId}
                onFileClick={onFileClick}
              />
            ) : (
              <FileNode
                key={child.id ?? child.file_path}
                file={child}
                depth={depth + 1}
                selectedId={selectedId}
                onFileClick={onFileClick}
              />
            ),
          )}
        </div>
      )}
    </div>
  );
}

// --- FileTree ---

/**
 * Renders a collapsible file tree from a flat list of indexed files.
 *
 * Props:
 *   files      – Array<{ id, file_path, language, size_bytes }>
 *   selectedId – id of the currently selected file, or null
 *   onFileClick– (file) => void, called when a file row is clicked
 *   className  – optional extra classes for the root element
 */
export default function FileTree({
  files = [],
  selectedId = null,
  onFileClick,
  className,
}) {
  const tree = buildTree(files);
  const entries = sortedEntries(tree);

  if (files.length === 0) {
    return (
      <div
        className={cn(
          "flex flex-col items-center justify-center py-12 gap-2",
          className,
        )}
      >
        <VscFolder className="text-3xl text-text-subtle" />
        <p className="text-xs text-text-subtle">No files indexed</p>
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col select-none overflow-y-auto", className)}>
      {entries.map((entry) =>
        entry._type === "folder" ? (
          <FolderNode
            key={entry.name}
            name={entry.name}
            node={entry}
            depth={0}
            selectedId={selectedId}
            onFileClick={onFileClick}
            defaultOpen
          />
        ) : (
          <FileNode
            key={entry.id ?? entry.file_path}
            file={entry}
            depth={0}
            selectedId={selectedId}
            onFileClick={onFileClick}
          />
        ),
      )}
    </div>
  );
}
