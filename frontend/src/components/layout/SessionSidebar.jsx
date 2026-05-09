import Card from "@/components/ui/Card";
import NewSessionButton from "@/components/session/NewSessionButton";
import SessionEntry from "../session/SessionEntry";

export default function SessionSidebar({ sessions }) {
  return (
    <Card className="w-72 h-screen p-4 flex flex-col">
      {/* New Sessions */}
      <h2 className="text-sm font-light mb-4 uppercase">Sessions</h2>
      <NewSessionButton />

      {/* Sessions */}
      <h2 className="text-sm font-light mt-6 mb-4 uppercase">
        Recent Activity
      </h2>
      <div className="mt-4 flex-1 overflow-y-auto flex flex-col gap-2">
        {sessions.map((session) => (
          <SessionEntry
            title={session.title}
            repoName={session.repoName}
            status={session.status}
            lastActive={session.lastActive}
            isActive={session.isActive}
            key={session.id}
          />
        ))}
      </div>
    </Card>
  );
}
