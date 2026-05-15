import { useState } from "react";
import { LuCircleAlert, LuChevronsRight, LuX } from "react-icons/lu";

import Header from "./Header";
import Panel from "./Panel";
import Sidebar from "./Sidebar";
import FileTreePanel from "@/components/files/FileTreePanel";
import FileView from "@/components/files/FileView";
import ChatPanel from "@/components/chat/ChatPanel";
import { IngestionView } from "@/pages/IngestionPage";
import NewSessionModal from "@/components/session/NewSessionModal";

const COLLAPSED_W = 40;

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

function RepoErrorPanel({ errorMessage, onRetry, retrying }) {
  return (
    <div className="flex-1 h-full flex flex-col items-center justify-center gap-6 p-8 bg-surface">
      <div
        className="w-16 h-16 rounded-full flex items-center justify-center"
        style={{ border: "2px solid var(--color-error)" }}
      >
        <LuCircleAlert size={28} style={{ color: "var(--color-error)" }} />
      </div>
      <div className="text-center flex flex-col gap-2">
        <p className="text-xs uppercase tracking-widest text-text-subtle">
          Ingestion failed
        </p>
        <p className="text-sm font-mono text-text max-w-xs">
          {errorMessage ?? "Repository not found or is private"}
        </p>
      </div>
      <button
        onClick={onRetry}
        disabled={retrying}
        className="px-8 py-2.5 bg-text text-black text-sm font-semibold uppercase tracking-widest cursor-pointer hover:bg-text-muted transition-colors duration-150 disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {retrying ? "Retrying\u2026" : "Retry Ingestion"}
      </button>
    </div>
  );
}

export default function AppLayout({
  sessions = [],
  activeSession = null,
  repoName = "owner/repo",
  files = [],
  messages = [],
  onSend,
  isLoading = false,
  getFileContent,
  onSelectSession,
  onCreateSession,
  onIngestionComplete,
  onIngestionFailed,
  onRetryIngestion,
  hasRepoAccess = false,
  onRenameSession,
  onDeleteSession,
}) {
  const [retrying, setRetrying] = useState(false);

  const handleRetry = async () => {
    setRetrying(true);
    try {
      await onRetryIngestion?.();
    } finally {
      setRetrying(false);
    }
  };
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [fileTreeOpen, setFileTreeOpen] = useState(true);

  const [sidebarWidth, setSidebarWidth] = useState(240);
  const [fileTreeWidth, setFileTreeWidth] = useState(220);
  const [fileViewWidth, setFileViewWidth] = useState(420);

  const [openFile, setOpenFile] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);

  const handleFileClick = async (file) => {
    const filename = file.file_path.split("/").pop();
    const content = getFileContent ? await getFileContent(file) : "";
    setOpenFile({ id: file.id, filename, content });
  };

  const handleModalSubmit = async (data) => {
    setModalOpen(false);
    if (onCreateSession) await onCreateSession(data);
  };

  const effectiveSidebarWidth = sidebarOpen ? sidebarWidth : COLLAPSED_W;
  const effectiveFileTreeWidth = fileTreeOpen ? fileTreeWidth : COLLAPSED_W;

  return (
    <>
      <div className="flex flex-col h-screen bg-surface overflow-hidden">
        <Header activeSession={activeSession} />

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
              onSelectSession={onSelectSession}
              onNewSession={() => setModalOpen(true)}
              onRenameSession={onRenameSession}
              onDeleteSession={onDeleteSession}
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

          {/* ── Main view ── */}
          <div className="flex-1 min-w-0 overflow-hidden">
            {activeSession && PROCESSING_STATUSES.has(activeSession.status) ? (
              <IngestionView
                sessionId={activeSession.id}
                onComplete={onIngestionComplete}
                onFailed={onIngestionFailed}
              />
            ) : activeSession?.status === "failed" ? (
              <RepoErrorPanel
                errorMessage={activeSession.errorMessage}
                onRetry={handleRetry}
                retrying={retrying}
              />
            ) : (
              <ChatPanel
                messages={messages}
                onSend={onSend}
                isLoading={isLoading}
              />
            )}
          </div>

          {/* ── File View ── */}
          {openFile && (
            <Panel
              width={fileViewWidth}
              side="left"
              onDragStart={makeResizer(setFileViewWidth, 280, 900, true)}
            >
              <div className="relative h-full border-l border-border overflow-hidden">
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

      <NewSessionModal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        onSubmit={handleModalSubmit}
        hasRepoAccess={hasRepoAccess}
      />
    </>
  );
}
