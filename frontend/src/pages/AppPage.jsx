import { useState, useEffect, useCallback, useRef } from "react";
import AppLayout from "@components/layout/AppLayout";
import {
  listSessions,
  createSession as apiCreateSession,
  updateSession,
  deleteSession,
  reingestSession,
} from "@api/sessions";
import { streamChat, getChatHistory } from "@api/chat";
import { listFiles, getFileContent as apiGetFileContent } from "@api/files";

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
  const [messages, setMessages] = useState([]);
  const [files, setFiles] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);

  // Keeps a ref to the abort function so we can cancel mid-stream on unmount
  // or when the user switches sessions.
  const abortStreamRef = useRef(null);

  // Load session list on mount.
  useEffect(() => {
    listSessions()
      .then(({ sessions: raw }) => setSessions(raw.map(normalizeSession)))
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

  const handleSelectSession = useCallback((id) => setSelectedId(id), []);

  const handleCreateSession = useCallback(async ({ url, title }) => {
    const raw = await apiCreateSession(url, title);
    const session = {
      id: raw.session_id,
      title: raw.title ?? `${raw.owner}/${raw.name}`,
      repoName: `${raw.owner}/${raw.name}`,
      status: raw.status ?? "pending",
      lastActive: raw.created_at,
    };
    setSessions((prev) => [session, ...prev]);
    setSelectedId(session.id);
    return session;
  }, []);

  const handleRenameSession = useCallback(async (id, newTitle) => {
    await updateSession(id, newTitle);
    setSessions((prev) =>
      prev.map((s) => (s.id === id ? { ...s, title: newTitle } : s)),
    );
  }, []);

  const handleDeleteSession = useCallback(async (id) => {
    await deleteSession(id);
    setSessions((prev) => prev.filter((s) => s.id !== id));
    setSelectedId((prev) => (prev === id ? null : prev));
  }, []);

  const handleIngestionComplete = useCallback(() => {
    setSessions((prev) =>
      prev.map((s) =>
        s.id === selectedId ? { ...s, status: "completed" } : s,
      ),
    );
  }, [selectedId]);

  const handleIngestionFailed = useCallback(
    (errorMessage) => {
      setSessions((prev) =>
        prev.map((s) =>
          s.id === selectedId
            ? { ...s, status: "failed", errorMessage: errorMessage ?? null }
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
      onRenameSession={handleRenameSession}
      onDeleteSession={handleDeleteSession}
    />
  );
}
