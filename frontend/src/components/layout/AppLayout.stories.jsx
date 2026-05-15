import { useState } from "react";
import { MemoryRouter } from "react-router-dom";
import AppLayout from "./AppLayout";

// ── Mock data ──────────────────────────────────────────────────────────────

const SESSIONS = [
  {
    id: 1,
    title: "Auth service review",
    repoName: "acme/auth-service",
    status: "completed",
    lastActive: new Date(Date.now() - 5 * 60 * 1000).toISOString(),
    isActive: true,
  },
  {
    id: 2,
    title: "Frontend onboarding",
    repoName: "acme/frontend",
    status: "processing",
    lastActive: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
    isActive: false,
  },
  {
    id: 3,
    title: "Data pipeline docs",
    repoName: "acme/data-pipeline",
    status: "failed",
    lastActive: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
    isActive: false,
  },
];

const FILES = [
  { id: 1, file_path: "app/__init__.py", language: "python", size_bytes: 0 },
  { id: 2, file_path: "app/main.py", language: "python", size_bytes: 1240 },
  { id: 3, file_path: "app/config.py", language: "python", size_bytes: 890 },
  { id: 4, file_path: "app/api/dependencies.py", language: "python", size_bytes: 600 },
  { id: 5, file_path: "app/api/routes/auth.py", language: "python", size_bytes: 1800 },
  { id: 6, file_path: "app/db/models.py", language: "python", size_bytes: 2100 },
  { id: 7, file_path: "README.md", language: "markdown", size_bytes: 2400 },
];

const MOCK_CONTENTS = {
  "app/__init__.py": "",
  "app/main.py": `from fastapi import FastAPI\nfrom app.api.routes import auth, sessions\n\napp = FastAPI(title="Codebase Onboarding Agent")\n\napp.include_router(auth.router, prefix="/auth")\napp.include_router(sessions.router, prefix="/sessions")\n`,
  "app/config.py": `from pydantic_settings import BaseSettings\n\nclass Settings(BaseSettings):\n    database_url: str\n    secret_key: str\n\nsettings = Settings()\n`,
  "README.md": `# Codebase Onboarding Agent\n\nAn AI-powered tool that helps developers quickly understand unfamiliar codebases.\n`,
};

const t = (minsAgo) => new Date(Date.now() - minsAgo * 60 * 1000).toISOString();

const INITIAL_MESSAGES = [
  {
    id: 1,
    role: "user",
    content: "What does the authentication flow look like?",
    createdAt: t(10),
  },
  {
    id: 2,
    role: "assistant",
    content: `Authentication uses **JWT tokens**:\n\n1. Client POSTs credentials to \`/auth/login\`\n2. Server verifies and returns a signed JWT\n3. Client sends the token in the \`Authorization\` header\n\nClick **app/api/dependencies.py** in the file tree to see the \`get_current_user\` dependency.`,
    createdAt: t(9),
  },
];

// ── Interactive wrapper ────────────────────────────────────────────────────

function InteractiveAppLayout({ initialSessions = SESSIONS }) {
  const [sessions, setSessions] = useState(initialSessions);
  const [selectedId, setSelectedId] = useState(initialSessions[0]?.id ?? null);
  const [messages, setMessages] = useState(INITIAL_MESSAGES);
  const [isLoading, setIsLoading] = useState(false);

  const activeSession = sessions.find((s) => s.id === selectedId) ?? null;

  const sessionsWithActive = sessions.map((s) => ({
    ...s,
    isActive: s.id === selectedId,
  }));

  const handleSelectSession = (id) => setSelectedId(id);

  const handleCreateSession = ({ url, title }) => {
    const newSession = {
      id: Date.now(),
      title: title || url.split("/").slice(-1)[0],
      repoName: url.replace("https://github.com/", ""),
      status: "processing",
      lastActive: new Date().toISOString(),
      isActive: false,
    };
    setSessions((prev) => [newSession, ...prev]);
    setSelectedId(newSession.id);
  };

  const handleSend = (text) => {
    if (!text.trim()) return;
    setMessages((prev) => [
      ...prev,
      { id: prev.length + 1, role: "user", content: text, createdAt: new Date().toISOString() },
    ]);
    setIsLoading(true);
    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        { id: prev.length + 1, role: "assistant", content: "This is a simulated assistant response.", createdAt: new Date().toISOString() },
      ]);
      setIsLoading(false);
    }, 1200);
  };

  const getFileContent = async (file) =>
    MOCK_CONTENTS[file.file_path] ?? `# ${file.file_path}\n# (no mock content)`;

  return (
    <AppLayout
      sessions={sessionsWithActive}
      activeSession={activeSession}
      repoName={activeSession?.repoName ?? "acme/auth-service"}
      files={FILES}
      messages={messages}
      onSend={handleSend}
      isLoading={isLoading}
      getFileContent={getFileContent}
      onSelectSession={handleSelectSession}
      onCreateSession={handleCreateSession}
    />
  );
}

// ── Stories ───────────────────────────────────────────────────────────────

export default {
  title: "Components/Layout/AppLayout",
  component: AppLayout,
  parameters: { layout: "fullscreen" },
  decorators: [
    (Story) => (
      <MemoryRouter>
        <Story />
      </MemoryRouter>
    ),
  ],
};

export const Default = {
  render: () => <InteractiveAppLayout />,
};

export const NoSessions = {
  render: () => <InteractiveAppLayout initialSessions={[]} />,
};
