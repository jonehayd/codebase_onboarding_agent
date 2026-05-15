import MessageList from "./MessageList";

const t = (minsAgo) => new Date(Date.now() - minsAgo * 60 * 1000).toISOString();

const CONVERSATION = [
  {
    id: 1,
    role: "user",
    content: "What does the authentication flow look like in this codebase?",
    createdAt: t(10),
  },
  {
    id: 2,
    role: "assistant",
    content: `The authentication flow uses **JWT tokens**. Here's the high-level sequence:

1. The client sends credentials to \`POST /auth/login\`
2. The server validates them and returns a signed JWT
3. The client stores the token and sends it in the \`Authorization\` header on every subsequent request

Tokens expire after 24 hours.`,
    createdAt: t(9),
  },
  {
    id: 3,
    role: "user",
    content: "Show me the dependency that validates the token on each request.",
    createdAt: t(5),
  },
  {
    id: 4,
    role: "assistant",
    content: `Here's the \`get_current_user\` dependency used to guard protected routes:

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

export default {
  title: "Components/Chat/MessageList",
  component: MessageList,
  decorators: [
    (Story) => (
      <div className="bg-surface max-w-2xl min-h-96">
        <Story />
      </div>
    ),
  ],
};

export const Default = {
  args: { messages: CONVERSATION },
};

export const Empty = {
  args: { messages: [] },
};

export const SingleUserMessage = {
  args: {
    messages: [
      {
        id: 1,
        role: "user",
        content: "Hey, what does this codebase do?",
        createdAt: t(1),
      },
    ],
  },
};
