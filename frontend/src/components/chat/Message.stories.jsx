import Message from "./Message";

export default {
  title: "Components/Chat/Message",
  component: Message,
  argTypes: {
    role: {
      control: "select",
      options: ["user", "assistant"],
    },
    content: { control: "text" },
    createdAt: { control: "text" },
  },
  decorators: [
    (Story) => (
      <div className="bg-base p-4 max-w-2xl">
        <Story />
      </div>
    ),
  ],
};

const now = new Date().toISOString();
const fiveMinutesAgo = new Date(Date.now() - 1000 * 60 * 5).toISOString();

export const UserMessage = {
  args: {
    role: "user",
    content: "What does the authentication flow look like in this codebase?",
    createdAt: fiveMinutesAgo,
  },
};

export const AssistantMessage = {
  args: {
    role: "assistant",
    content:
      "The authentication flow uses JWT tokens. When a user logs in, the server validates credentials and returns a signed token that is stored client-side and sent with subsequent requests.",
    createdAt: now,
  },
};

export const AssistantWithMarkdown = {
  args: {
    role: "assistant",
    content: `Here's an overview of the authentication flow:

**1. Login Request**
The client sends credentials to \`POST /auth/login\`.

**2. Token Generation**
The server validates the credentials and returns a JWT.

**3. Authenticated Requests**
All subsequent requests include the token in the \`Authorization\` header.

> Tokens expire after 24 hours and must be refreshed.`,
    createdAt: now,
  },
};

export const AssistantWithCodeBlock = {
  args: {
    role: "assistant",
    content: `The \`get_current_user\` dependency extracts and validates the JWT from the request:

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

This is used as a dependency in any route that requires authentication.`,
    createdAt: now,
  },
};

export const LongUserMessage = {
  args: {
    role: "user",
    content:
      "Can you walk me through how the ingestion pipeline processes a GitHub repository? I want to understand the chunking strategy, how files are filtered, and how the resulting chunks end up stored in the vector database.",
    createdAt: fiveMinutesAgo,
  },
};
