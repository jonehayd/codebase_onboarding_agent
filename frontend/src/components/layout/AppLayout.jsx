// components/layout/AppLayout.jsx
// Top-level layout. Manages panel visibility, widths, and the open file state.
// getFileContent(file) => Promise<string> is called when a file is clicked.

import { useState } from "react";
import { LuChevronsRight, LuX } from "react-icons/lu";

import Header from "./Header";
import Panel from "./Panel";
import Sidebar from "./Sidebar";
import FileTreePanel from "@/components/files/FileTreePanel";
import FileView from "@/components/files/FileView";
import ChatPanel from "@/components/chat/ChatPanel";
import { IngestionView } from "@/pages/IngestionPage";

const COLLAPSED_W = 40;

// Creates a mousedown handler that resizes `setter` by dragging.
// reversed=true flips the direction (for right-side panels with left-edge handles).
function makeResizer(setter, min, max, reversed = false) {
  return (e) => {
    e.preventDefault();
    const startX = e.clientX;
    const startW = e.currentTarget.parentElement.getBoundingClientRect().width;

    const onMove = (ev) => {
      const delta = ev.clientX - startX;
      const next = reversed ? startW - delta : startW + delta;
      setter(Math.max(min, Math.min(max, next)));
    };
    const onUp = () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  };
}

const PROCESSING_STATUSES = new Set(["pending", "processing"]);

export default function AppLayout({
  sessions = [],
  activeSession = null,
  repoName = "owner/repo",
  files = [],
  messages = [],
  onSend,
  isLoading = false,
  getFileContent,
}) {
  // Collapse state
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [fileTreeOpen, setFileTreeOpen] = useState(true);

  // Panel widths (when open)
  const [sidebarWidth, setSidebarWidth] = useState(240);
  const [fileTreeWidth, setFileTreeWidth] = useState(220);
  const [fileViewWidth, setFileViewWidth] = useState(420);

  // Currently open file in the viewer
  const [openFile, setOpenFile] = useState(null); // { id, filename, content }

  const handleFileClick = async (file) => {
    const filename = file.file_path.split("/").pop();
    const content = getFileContent ? await getFileContent(file) : "";
    setOpenFile({ id: file.id, filename, content });
  };

  const effectiveSidebarWidth = sidebarOpen ? sidebarWidth : COLLAPSED_W;
  const effectiveFileTreeWidth = fileTreeOpen ? fileTreeWidth : COLLAPSED_W;

  return (
    <div className="flex flex-col h-screen bg-surface overflow-hidden">
      <Header />

      <div className="flex flex-1 overflow-hidden min-h-0">
        {/* ── Session Sidebar ── */}
        <Panel
          width={effectiveSidebarWidth}
          onDragStart={
            sidebarOpen ? makeResizer(setSidebarWidth, 180, 420) : null
          }
        >
          <Sidebar
            sessions={sessions}
            open={sidebarOpen}
            onToggle={() => setSidebarOpen((o) => !o)}
          />
        </Panel>

        {/* ── File Tree ── */}
        <Panel
          width={effectiveFileTreeWidth}
          onDragStart={
            fileTreeOpen ? makeResizer(setFileTreeWidth, 160, 520) : null
          }
        >
          {fileTreeOpen ? (
            <FileTreePanel
              repoName={repoName}
              files={files}
              selectedId={openFile?.id ?? null}
              onFileClick={handleFileClick}
              onToggle={() => setFileTreeOpen(false)}
            />
          ) : (
            <div className="flex flex-col h-full bg-surface-raised border-r border-border items-center pt-2 overflow-hidden">
              <button
                onClick={() => setFileTreeOpen(true)}
                className="p-1.5 rounded text-text-muted hover:text-text hover:bg-surface-high transition-colors"
                title="Expand file tree"
              >
                <LuChevronsRight size={14} />
              </button>
            </div>
          )}
        </Panel>

        {/* ── Main view (flex-1, takes remaining space) ── */}
        <div className="flex-1 min-w-0 overflow-hidden">
          {activeSession && PROCESSING_STATUSES.has(activeSession.status) ? (
            <IngestionView sessionId={activeSession.id} />
          ) : (
            <ChatPanel
              messages={messages}
              onSend={onSend}
              isLoading={isLoading}
            />
          )}
        </div>

        {/* ── File View (slides in from the right when a file is open) ── */}
        {openFile && (
          <Panel
            width={fileViewWidth}
            side="left"
            onDragStart={makeResizer(setFileViewWidth, 280, 900, true)}
          >
            <div className="relative h-full border-l border-border overflow-hidden">
              {/* Close button overlaid on the title bar */}
              <button
                onClick={() => setOpenFile(null)}
                className="absolute top-1.5 right-2 z-30 p-1 rounded
                  text-text-muted hover:text-text hover:bg-surface-highest
                  transition-colors"
                title="Close file"
              >
                <LuX size={14} />
              </button>
              <FileView
                filename={openFile.filename}
                content={openFile.content}
              />
            </div>
          </Panel>
        )}
      </div>
    </div>
  );
}
