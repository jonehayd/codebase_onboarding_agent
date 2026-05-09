import { useState } from "react";
import FileTree from "./FileTree";

// --- Sample datasets ---

const PYTHON_FILES = [
  { id: 1, file_path: "app/__init__.py", language: "python", size_bytes: 0 },
  { id: 2, file_path: "app/main.py", language: "python", size_bytes: 1240 },
  { id: 3, file_path: "app/config.py", language: "python", size_bytes: 890 },
  {
    id: 4,
    file_path: "app/api/__init__.py",
    language: "python",
    size_bytes: 0,
  },
  {
    id: 5,
    file_path: "app/api/dependencies.py",
    language: "python",
    size_bytes: 600,
  },
  {
    id: 6,
    file_path: "app/api/schemas.py",
    language: "python",
    size_bytes: 1100,
  },
  {
    id: 7,
    file_path: "app/api/routes/__init__.py",
    language: "python",
    size_bytes: 0,
  },
  {
    id: 8,
    file_path: "app/api/routes/auth.py",
    language: "python",
    size_bytes: 1800,
  },
  {
    id: 9,
    file_path: "app/api/routes/sessions.py",
    language: "python",
    size_bytes: 4200,
  },
  {
    id: 10,
    file_path: "app/db/__init__.py",
    language: "python",
    size_bytes: 0,
  },
  {
    id: 11,
    file_path: "app/db/database.py",
    language: "python",
    size_bytes: 750,
  },
  {
    id: 12,
    file_path: "app/db/models.py",
    language: "python",
    size_bytes: 2100,
  },
  {
    id: 13,
    file_path: "app/services/__init__.py",
    language: "python",
    size_bytes: 0,
  },
  {
    id: 14,
    file_path: "app/services/analyze.py",
    language: "python",
    size_bytes: 3400,
  },
  {
    id: 15,
    file_path: "app/services/chat.py",
    language: "python",
    size_bytes: 2800,
  },
  { id: 16, file_path: "alembic.ini", language: "ini", size_bytes: 820 },
  { id: 17, file_path: "requirements.txt", language: "text", size_bytes: 340 },
  { id: 18, file_path: "README.md", language: "markdown", size_bytes: 2400 },
];

const FRONTEND_FILES = [
  { id: 1, file_path: "src/App.jsx", language: "javascript", size_bytes: 640 },
  { id: 2, file_path: "src/main.jsx", language: "javascript", size_bytes: 210 },
  { id: 3, file_path: "src/index.css", language: "css", size_bytes: 1400 },
  {
    id: 4,
    file_path: "src/pages/LoginPage.jsx",
    language: "javascript",
    size_bytes: 890,
  },
  {
    id: 5,
    file_path: "src/pages/IngestionPage.jsx",
    language: "javascript",
    size_bytes: 3200,
  },
  {
    id: 6,
    file_path: "src/components/ui/Card.jsx",
    language: "javascript",
    size_bytes: 210,
  },
  {
    id: 7,
    file_path: "src/components/ui/Header.jsx",
    language: "javascript",
    size_bytes: 640,
  },
  {
    id: 8,
    file_path: "src/components/ui/FileTree.jsx",
    language: "javascript",
    size_bytes: 3100,
  },
  {
    id: 9,
    file_path: "src/api/sessions.js",
    language: "javascript",
    size_bytes: 1200,
  },
  {
    id: 10,
    file_path: "src/lib/utils.ts",
    language: "typescript",
    size_bytes: 140,
  },
  { id: 11, file_path: "package.json", language: "json", size_bytes: 1100 },
  {
    id: 12,
    file_path: "vite.config.js",
    language: "javascript",
    size_bytes: 480,
  },
  { id: 13, file_path: "README.md", language: "markdown", size_bytes: 3200 },
  {
    id: 14,
    file_path: "eslint.config.js",
    language: "javascript",
    size_bytes: 290,
  },
];

// --- Story wrapper ---

const Panel = ({ children }) => (
  <div className="bg-surface-raised border border-border w-72 h-120 flex flex-col">
    <div className="flex-1 overflow-y-auto py-2">{children}</div>
  </div>
);

// --- Stories ---

export default {
  title: "UI/FileTree",
  component: FileTree,
  decorators: [
    (Story) => (
      <div className="bg-base min-h-screen p-8 flex items-start gap-8">
        <Story />
      </div>
    ),
  ],
};

export const PythonBackend = {
  render: () => (
    <Panel>
      <FileTree files={PYTHON_FILES} />
    </Panel>
  ),
};

export const ReactFrontend = {
  render: () => (
    <Panel>
      <FileTree files={FRONTEND_FILES} />
    </Panel>
  ),
};

export const WithSelectedFile = {
  render: () => {
    const [selectedId, setSelectedId] = useState(9);
    return (
      <Panel>
        <FileTree
          files={FRONTEND_FILES}
          selectedId={selectedId}
          onFileClick={(file) => setSelectedId(file.id)}
        />
      </Panel>
    );
  },
};

export const MixedRepo = {
  render: () => (
    <Panel>
      <FileTree
        files={[
          ...PYTHON_FILES.slice(0, 6),
          ...FRONTEND_FILES.slice(0, 6),
          {
            id: 100,
            file_path: "docker-compose.yml",
            language: "yaml",
            size_bytes: 640,
          },
          {
            id: 101,
            file_path: ".github/workflows/ci.yml",
            language: "yaml",
            size_bytes: 880,
          },
          {
            id: 102,
            file_path: "docs/overview.md",
            language: "markdown",
            size_bytes: 1200,
          },
          {
            id: 103,
            file_path: "docs/api.md",
            language: "markdown",
            size_bytes: 3400,
          },
        ]}
      />
    </Panel>
  ),
};

export const Empty = {
  render: () => (
    <Panel>
      <FileTree files={[]} />
    </Panel>
  ),
};

export const FlatRootFiles = {
  render: () => (
    <Panel>
      <FileTree
        files={[
          { id: 1, file_path: "main.py", language: "python", size_bytes: 400 },
          {
            id: 2,
            file_path: "README.md",
            language: "markdown",
            size_bytes: 900,
          },
          {
            id: 3,
            file_path: "requirements.txt",
            language: "text",
            size_bytes: 200,
          },
          {
            id: 4,
            file_path: "package.json",
            language: "json",
            size_bytes: 700,
          },
          { id: 5, file_path: "index.html", language: "html", size_bytes: 500 },
          { id: 6, file_path: "styles.css", language: "css", size_bytes: 300 },
          {
            id: 7,
            file_path: "app.ts",
            language: "typescript",
            size_bytes: 1200,
          },
        ]}
      />
    </Panel>
  ),
};
