// components/chat/Message.jsx

import AssistantMessageContent from "./AssistantMessageContent";

function formatTimestamp(isoString) {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

export default function Message({ role, content, createdAt }) {
  const isUser = role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {/* bubble */}
      <div
        className={`max-w-[90%] flex flex-col gap-1 ${isUser ? "items-end" : "items-start"}`}
      >
        <div
          className={`px-3 py-2 rounded-lg text-sm
          ${
            isUser
              ? "bg-surface-raised text-text leading-relaxed"
              : "bg-surface-highest border border-border w-full"
          }`}
        >
          {isUser ? content : <AssistantMessageContent content={content} />}
        </div>
        <span className="text-xs text-text-subtle px-1">
          {formatTimestamp(createdAt)}
        </span>
      </div>
    </div>
  );
}
