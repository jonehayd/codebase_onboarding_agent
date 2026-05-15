import Message from "./Message";

export default function MessageList({ messages }) {
  return (
    <div className="flex flex-col gap-4 px-4 py-6">
      {messages.map((message) => (
        <Message
          key={message.id}
          role={message.role}
          content={message.content}
          createdAt={message.createdAt}
        />
      ))}
    </div>
  );
}
