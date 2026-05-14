import { LuChevronsRight } from "react-icons/lu";
import SessionSidebar from "@/components/session/SessionSidebar";

export default function Sidebar({ sessions, open, onToggle, onSelectSession, onNewSession, onRenameSession, onDeleteSession }) {
  if (!open) {
    return (
      <div className="flex flex-col h-full bg-surface-elevated border-r border-border items-center pt-2 overflow-hidden">
        <button
          onClick={onToggle}
          className="p-1.5 rounded text-text-muted hover:text-text hover:bg-surface-raised transition-colors"
          title="Expand sidebar"
        >
          <LuChevronsRight size={14} />
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-surface-elevated border-r border-border overflow-hidden">
      <SessionSidebar
        sessions={sessions}
        onToggle={onToggle}
        onSelectSession={onSelectSession}
        onNewSession={onNewSession}
        onRenameSession={onRenameSession}
        onDeleteSession={onDeleteSession}
      />
    </div>
  );
}
