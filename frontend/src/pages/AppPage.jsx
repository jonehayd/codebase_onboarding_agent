import { useState, useEffect, useCallback, useRef } from "react";
import { toast } from "sonner";
import AppLayout from "@components/layout/AppLayout";
import {
  listSessions,
  createSession as apiCreateSession,
  updateSession,
  deleteSession,
  checkFreshness,
  reingestSession,
} from "@api/sessions";
import { streamChat, getChatHistory } from "@api/chat";
import { listFiles, getFileContent as apiGetFileContent } from "@api/files";
import { getMe } from "@api/auth";

const PROCESSING_STATUSES = new Set(["pending", "processing"]);

// Normalize a SessionSummary from the backend into the shape the UI expects.
function normalizeSession(s) {
  return {
    id: s.session_id,
    title: s.title ?? `${s.owner}/${s.name}`,
    repoName: `${s.owner}/${s.name}`,
    status: s.status,
    lastActive: s.last_active_at,
  };
}

export default function AppPage() {
  const [sessions, setSessions] = useState([]);
  const [selectedId, setSelectedId] = useState(null);

  const persistSelectedId = useCallback((id) => {
    setSelectedId(id);
    if (id == null) localStorage.removeItem("selectedSessionId");
    else localStorage.setItem("selectedSessionId", id);
  }, []);
  const [messages, setMessages] = useState([]);
  const [files, setFiles] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [hasRepoAccess, setHasRepoAccess] = useState(false);

  // Keeps a ref to the abort function so we can cancel mid-stream on unmount
  // or when the user switches sessions.
  const abortStreamRef = useRef(null);

  // Load session list on mount.
  useEffect(() => {
    listSessions()
      .then(({ sessions: raw }) => {
        const normalized = raw.map(normalizeSession);
        setSessions(normalized);
        const stored = parseInt(localStorage.getItem("selectedSessionId"), 10);
        if (stored && normalized.some((s) => s.id === stored)) {
          setSelectedId(stored);
        }
      })
      .catch(() => {});
    getMe()
      .then((u) => setHasRepoAccess(u.has_repo_access ?? false))
      .catch(() => {});
  }, []);

  const activeSession = sessions.find((s) => s.id === selectedId) ?? null;
  const repoName = activeSession?.repoName ?? "";

  // Load history and files whenever the selected session changes,
  // but only once it has finished ingestion.
  useEffect(() => {
    abortStreamRef.current?.();
    setMessages([]);
    setFiles([]);

    if (!selectedId || PROCESSING_STATUSES.has(activeSession?.status)) return;

    getChatHistory(selectedId)
      .then(({ messages: msgs }) =>
        setMessages(
          msgs.map((m, i) => ({
            id: i,
            role: m.role,
            content: m.content,
            createdAt: m.created_at,
          })),
        ),
      )
      .catch(() => {});

    listFiles(selectedId)
      .then(({ files: f }) => setFiles(f))
      .catch(() => {});
  }, [selectedId, activeSession?.status]);

  // Cancel any in-flight stream when the component unmounts.
  useEffect(() => () => abortStreamRef.current?.(), []);

  // When a completed session is selected, check for new commits and auto-reingest if stale.
  useEffect(() => {
    if (!selectedId || activeSession?.status !== "completed") return;

    checkFreshness(selectedId)
      .then(({ is_stale }) => {
        if (!is_stale) return;
        return reingestSession(selectedId).then(() => {
          setSessions((prev) =>
            prev.map((s) =>
              s.id === selectedId ? { ...s, status: "pending" } : s,
            ),
          );
          toast.info("Applying latest changes", {
            description:
              "New commits were detected. Re-syncing the repository now.",
          });
        });
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId]);

  const handleSelectSession = useCallback(
    (id) => persistSelectedId(id),
    [persistSelectedId],
  );

  const handleCreateSession = useCallback(
    async ({ url, title }) => {
      const raw = await apiCreateSession(url, title);
      const session = {
        id: raw.session_id,
        title: raw.title ?? title ?? `${raw.owner}/${raw.name}`,
        repoName: `${raw.owner}/${raw.name}`,
        status: raw.status ?? "pending",
        lastActive: raw.created_at,
      };
      setSessions((prev) => [session, ...prev]);
      persistSelectedId(session.id);
      return session;
    },
    [persistSelectedId],
  );

  const handleRenameSession = useCallback(async (id, newTitle) => {
    await updateSession(id, newTitle);
    setSessions((prev) =>
      prev.map((s) => (s.id === id ? { ...s, title: newTitle } : s)),
    );
  }, []);

  const handleDeleteSession = useCallback(
    async (id) => {
      await deleteSession(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (selectedId === id) persistSelectedId(null);
    },
    [selectedId, persistSelectedId],
  );

  const handleIngestionComplete = useCallback(() => {
    setSessions((prev) =>
      prev.map((s) =>
        s.id === selectedId ? { ...s, status: "completed" } : s,
      ),
    );
  }, [selectedId]);

  const handleIngestionFailed = useCallback(
    (errorMessage, wasCancelled = false) => {
      setSessions((prev) =>
        prev.map((s) =>
          s.id === selectedId
            ? {
                ...s,
                status: "failed",
                errorMessage: errorMessage ?? null,
                wasCancelled,
              }
            : s,
        ),
      );
    },
    [selectedId],
  );

  const handleRetryIngestion = useCallback(async () => {
    if (!selectedId) return;
    await reingestSession(selectedId);
    setSessions((prev) =>
      prev.map((s) =>
        s.id === selectedId
          ? { ...s, status: "pending", errorMessage: null }
          : s,
      ),
    );
  }, [selectedId]);

  const handleSend = useCallback(
    (question) => {
      if (!selectedId || isStreaming) return;

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

      abortStreamRef.current = streamChat(
        selectedId,
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
          abortStreamRef.current = null;
        },
        () => {
          setIsStreaming(false);
          abortStreamRef.current = null;
        },
      );
    },
    [selectedId, isStreaming],
  );

  const getFileContent = useCallback(
    async (file) => {
      const { content } = await apiGetFileContent(selectedId, file.id);
      return content;
    },
    [selectedId],
  );

  const sessionsWithActive = sessions.map((s) => ({
    ...s,
    isActive: s.id === selectedId,
  }));

  return (
    <AppLayout
      sessions={sessionsWithActive}
      activeSession={activeSession}
      repoName={repoName}
      files={files}
      messages={messages}
      onSend={handleSend}
      isLoading={isStreaming}
      getFileContent={getFileContent}
      onSelectSession={handleSelectSession}
      onCreateSession={handleCreateSession}
      onIngestionComplete={handleIngestionComplete}
      onIngestionFailed={handleIngestionFailed}
      onRetryIngestion={handleRetryIngestion}
      hasRepoAccess={hasRepoAccess}
      onRenameSession={handleRenameSession}
      onDeleteSession={handleDeleteSession}
    />
  );
}
