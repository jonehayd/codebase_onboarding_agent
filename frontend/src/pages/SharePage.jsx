import { useState, useEffect, useRef, useCallback } from "react";
import { useParams } from "react-router-dom";
import { LuChevronsRight, LuX } from "react-icons/lu";
import {
  getSharedRepo,
  getSharedHistory,
  listSharedFiles,
  getSharedFileContent,
  streamSharedChat,
} from "@/api/share";
import Panel from "@/components/layout/Panel";
import FileTreePanel from "@/components/files/FileTreePanel";
import FileView from "@/components/files/FileView";
import ChatPanel from "@/components/chat/ChatPanel";

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

export default function SharePage() {
  const { token } = useParams();
  const [repoInfo, setRepoInfo] = useState(null);
  const [error, setError] = useState(null);
  const [messages, setMessages] = useState([]);
  const [files, setFiles] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef(null);

  const [fileTreeOpen, setFileTreeOpen] = useState(true);
  const [fileTreeWidth, setFileTreeWidth] = useState(220);
  const [fileViewWidth, setFileViewWidth] = useState(420);
  const [openFile, setOpenFile] = useState(null);

  // Load repo info, history, and files on mount
  useEffect(() => {
    getSharedRepo(token)
      .then((info) => {
        setRepoInfo(info);
        return Promise.all([getSharedHistory(token), listSharedFiles(token)]);
      })
      .then(([historyData, filesData]) => {
        setMessages(
          historyData.messages.map((m, i) => ({
            id: i,
            role: m.role,
            content: m.content,
            createdAt: m.created_at,
          })),
        );
        setFiles(filesData.files);
      })
      .catch((err) => setError(err.message));
  }, [token]);

  useEffect(() => () => abortRef.current?.(), []);

  const handleFileClick = useCallback(
    async (file) => {
      const filename = file.file_path.split("/").pop();
      const data = await getSharedFileContent(token, file.id);
      setOpenFile({ id: file.id, filename, content: data.content });
    },
    [token],
  );

  const handleSend = useCallback(
    (question) => {
      if (isStreaming) return;

      const userMsg = {
        id: `u-${Date.now()}`,
        role: "user",
        content: question,
        createdAt: new Date().toISOString(),
      };
      const assistantId = `a-${Date.now()}`;
      const assistantMsg = {
        id: assistantId,
        role: "assistant",
        content: "",
        createdAt: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsStreaming(true);

      abortRef.current = streamSharedChat(
        token,
        question,
        (chunk) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, content: m.content + chunk } : m,
            ),
          );
        },
        () => {
          setIsStreaming(false);
          abortRef.current = null;
        },
        () => {
          setIsStreaming(false);
          abortRef.current = null;
        },
      );
    },
    [token, isStreaming],
  );

  if (error) {
    return (
      <div className="min-h-screen bg-base flex items-center justify-center">
        <div className="text-center">
          <p className="text-error text-sm mb-2">
            Share link not found or revoked
          </p>
          <p className="text-text-subtle text-xs">{error}</p>
        </div>
      </div>
    );
  }

  if (!repoInfo) {
    return (
      <div className="min-h-screen bg-base flex items-center justify-center">
        <p className="text-text-muted text-sm">Loading…</p>
      </div>
    );
  }

  const effectiveFileTreeWidth = fileTreeOpen ? fileTreeWidth : COLLAPSED_W;

  return (
    <div className="flex flex-col h-screen bg-surface overflow-hidden">
      <header className="w-full h-16 bg-color-surface flex items-center border-b border-color-border px-4 shrink-0">
        <h1 className="text-xl font-semibold text-color-text">
          CODEBASE_ONBOARDING_AGENT
        </h1>
        <span className="ml-4 text-sm font-mono text-text-muted">
          {repoInfo.owner}/{repoInfo.name}
        </span>
        <span className="ml-3 text-xs text-text-subtle uppercase tracking-widest">
          · shared view
        </span>
      </header>

      <div className="flex flex-1 overflow-hidden min-h-0">
        {/* ── File Tree ── */}
        <Panel
          width={effectiveFileTreeWidth}
          onDragStart={
            fileTreeOpen ? makeResizer(setFileTreeWidth, 160, 520) : null
          }
        >
          {fileTreeOpen ? (
            <FileTreePanel
              repoName={`${repoInfo.owner}/${repoInfo.name}`}
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

        {/* ── Chat ── */}
        <div className="flex-1 min-w-0 overflow-hidden">
          <ChatPanel
            messages={messages}
            onSend={handleSend}
            isLoading={isStreaming}
          />
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
  );
}
