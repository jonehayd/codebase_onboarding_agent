// components/chat/ChatPanel.jsx

import { useEffect, useRef } from "react";
import MessageList from "./MessageList";
import ChatInput from "./ChatInput";

export default function ChatPanel({ messages, onSend, isLoading }) {
  const bottomRef = useRef(null);
  const scrollRef = useRef(null);
  const userScrolled = useRef(false);

  // Re-enable auto-scroll when the user scrolls back to the bottom.
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const onScroll = () => {
      const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 60;
      if (atBottom) userScrolled.current = false;
      else userScrolled.current = true;
    };
    el.addEventListener("scroll", onScroll, { passive: true });
    return () => el.removeEventListener("scroll", onScroll);
  }, []);

  // Auto-scroll on new message content unless the user has scrolled away.
  useEffect(() => {
    if (!userScrolled.current) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  return (
    <div className="flex flex-col h-full">
      {/* scrollable message area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto">
          <MessageList messages={messages} />
          {isLoading && (
            <div className="px-4 pb-4">
              <div className="flex gap-1 px-3 py-2">
                <span className="w-1.5 h-1.5 rounded-full bg-text-muted animate-bounce [animation-delay:0ms]" />
                <span className="w-1.5 h-1.5 rounded-full bg-text-muted animate-bounce [animation-delay:150ms]" />
                <span className="w-1.5 h-1.5 rounded-full bg-text-muted animate-bounce [animation-delay:300ms]" />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* input pinned to bottom of flex column — no sticky needed */}
      <div className="shrink-0 pb-10">
        <div className="max-w-3xl mx-auto">
          <ChatInput onSend={onSend} />
        </div>
      </div>
    </div>
  );
}
