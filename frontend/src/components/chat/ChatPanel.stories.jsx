import { useState } from "react";
import ChatPanel from "./ChatPanel";

const t = (minsAgo) => new Date(Date.now() - minsAgo * 60 * 1000).toISOString();

const INITIAL_MESSAGES = [
  {
    id: 1,
    role: "user",
    content: "What does the authentication flow look like in this codebase?",
    createdAt: t(10),
  },
  {
    id: 2,
    role: "assistant",
    content: `The authentication flow uses **JWT tokens**. Here's the sequence:

1. Client sends credentials to \`POST /auth/login\`
2. Server validates and returns a signed JWT
3. Client attaches the token to every subsequent request via the \`Authorization\` header

Tokens expire after 24 hours.`,
    createdAt: t(9),
  },
  {
    id: 3,
    role: "user",
    content: "Show me the dependency that validates the token.",
    createdAt: t(5),
  },
  {
    id: 4,
    role: "assistant",
    content: `Here's the \`get_current_user\` dependency:

\`\`\`python
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    user_id: int = payload.get("sub")
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user
\`\`\`

Inject it into any route with \`Depends(get_current_user)\`.`,
    createdAt: t(4),
  },
];

function InteractiveChatPanel(args) {
  const [messages, setMessages] = useState(args.messages);
  const [isLoading, setIsLoading] = useState(false);

  const handleSend = (text) => {
    if (!text.trim()) return;
    const userMsg = {
      id: messages.length + 1,
      role: "user",
      content: text,
      createdAt: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);
    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          id: prev.length + 1,
          role: "assistant",
          content: "This is a simulated response from the assistant.",
          createdAt: new Date().toISOString(),
        },
      ]);
      setIsLoading(false);
    }, 1200);
  };

  return (
    <ChatPanel messages={messages} onSend={handleSend} isLoading={isLoading} />
  );
}

export default {
  title: "Components/Chat/ChatPanel",
  component: ChatPanel,
  decorators: [
    (Story) => (
      <div className="bg-surface h-screen">
        <Story />
      </div>
    ),
  ],
};

export const Default = {
  render: (args) => <InteractiveChatPanel {...args} />,
  args: { messages: INITIAL_MESSAGES },
};

export const Empty = {
  render: (args) => <InteractiveChatPanel {...args} />,
  args: { messages: [] },
};

export const Loading = {
  args: {
    messages: INITIAL_MESSAGES,
    onSend: () => {},
    isLoading: true,
  },
};
