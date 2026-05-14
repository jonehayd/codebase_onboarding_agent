import { LuChevronsLeft } from "react-icons/lu";
import Card from "@/components/ui/Card";
import NewSessionButton from "@/components/session/NewSessionButton";
import SessionEntry from "./SessionEntry";

export default function SessionSidebar({ sessions, onToggle, onSelectSession, onNewSession, onRenameSession, onDeleteSession }) {
  return (
    <Card className="w-full h-full p-4 flex flex-col overflow-hidden bg-surface-elevated">
      {/* Sessions header + collapse button */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-light uppercase">Sessions</h2>
        {onToggle && (
          <button
            onClick={onToggle}
            className="p-1.5 rounded text-text-muted hover:text-text hover:bg-surface-raised transition-colors"
            title="Collapse sidebar"
          >
            <LuChevronsLeft size={14} />
          </button>
        )}
      </div>

      <NewSessionButton onClick={onNewSession} />

      <h2 className="text-sm font-light mt-6 mb-4 uppercase">Recent Activity</h2>
      <div className="mt-4 flex-1 overflow-y-auto flex flex-col gap-2">
        {sessions.map((session) => (
          <SessionEntry
            key={session.id}
            title={session.title}
            repoName={session.repoName}
            status={session.status}
            lastActive={session.lastActive}
            isActive={session.isActive}
            onClick={() => onSelectSession?.(session.id)}
            onRename={(newTitle) => onRenameSession?.(session.id, newTitle)}
            onDelete={() => onDeleteSession?.(session.id)}
          />
        ))}
      </div>
    </Card>
  );
}
