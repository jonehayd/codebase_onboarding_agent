import { useState } from "react";
import FileView from "./FileView";

const FILES = [
  { id: 1, file_path: "app/__init__.py", language: "python", size_bytes: 0 },
  { id: 2, file_path: "app/main.py", language: "python", size_bytes: 1240 },
  { id: 3, file_path: "app/config.py", language: "python", size_bytes: 890 },
  {
    id: 4,
    file_path: "app/api/dependencies.py",
    language: "python",
    size_bytes: 600,
  },
  {
    id: 5,
    file_path: "app/api/routes/auth.py",
    language: "python",
    size_bytes: 1800,
  },
  {
    id: 6,
    file_path: "app/api/routes/sessions.py",
    language: "python",
    size_bytes: 4200,
  },
  {
    id: 7,
    file_path: "app/db/models.py",
    language: "python",
    size_bytes: 2100,
  },
  {
    id: 8,
    file_path: "app/services/analyze.py",
    language: "python",
    size_bytes: 3400,
  },
  { id: 9, file_path: "alembic.ini", language: "ini", size_bytes: 820 },
  { id: 10, file_path: "requirements.txt", language: "text", size_bytes: 340 },
  { id: 11, file_path: "README.md", language: "markdown", size_bytes: 2400 },
];

const Panel = ({ children }) => (
  <div className="bg-base h-screen w-64 flex">{children}</div>
);

export default {
  title: "Components/Files/FileView",
  component: FileView,
};

export const Default = {
  render: () => (
    <Panel>
      <FileView repoName="acme/auth-service" files={FILES} />
    </Panel>
  ),
};

export const WithSelectedFile = {
  render: () => {
    const [selectedId, setSelectedId] = useState(5);
    return (
      <Panel>
        <FileView
          repoName="acme/auth-service"
          files={FILES}
          selectedId={selectedId}
          onFileClick={(file) => setSelectedId(file.id)}
        />
      </Panel>
    );
  },
};

export const Empty = {
  render: () => (
    <Panel>
      <FileView repoName="acme/empty-repo" files={[]} />
    </Panel>
  ),
};
