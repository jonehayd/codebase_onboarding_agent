import { useState } from "react";
import { LuSend } from "react-icons/lu";

const MAX_CHARS = 1000;

export default function ChatInput({ onSend }) {
  const [message, setMessage] = useState("");
  const [focused, setFocused] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const count = message.length;
  const tooLong = count > MAX_CHARS;
  const isEmpty = message.trim().length === 0;
  const hasError = tooLong;

  const handleSubmit = (e) => {
    e.preventDefault();
    setSubmitted(true);
    if (!tooLong && !isEmpty) {
      onSend(message);
      setMessage("");
      setSubmitted(false);
    }
  };

  return (
    <div className="flex flex-col bg-surface-raised border-t border-border p-3">
      <div
        className={`flex items-center border transition-colors duration-150 ${
          hasError
            ? "border-error"
            : focused
              ? "border-border-focus"
              : "border-border"
        }`}
      >
        <form onSubmit={handleSubmit} className="flex items-center w-full">
          <input
            className="flex-1 bg-surface px-3 py-2 text-sm text-text placeholder:text-placeholder outline-none"
            type="text"
            placeholder="Ask a question..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
          />
          <button
            type="submit"
            disabled={isEmpty || tooLong}
            className="px-3 py-2 text-text-subtle hover:text-text transition-colors duration-150 cursor-pointer bg-surface disabled:cursor-not-allowed disabled:text-text-muted disabled:hover:text-text-muted"
          >
            <LuSend />
          </button>
        </form>
      </div>
      <div className="flex justify-between items-center px-1">
        <span className="text-xs text-error h-4">
          {tooLong && `Message cannot exceed ${MAX_CHARS} characters.`}
        </span>
        <span
          className={`text-xs ${tooLong ? "text-error" : "text-text-subtle"}`}
        >
          {count} / {MAX_CHARS}
        </span>
      </div>
    </div>
  );
}
