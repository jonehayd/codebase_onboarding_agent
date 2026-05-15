import { Link } from "react-router-dom";
import { RiTerminalBoxFill, RiGithubFill } from "react-icons/ri";
import { LuChevronsRight } from "react-icons/lu";

const REPO_URL = "https://github.com/jonehayd/codebase_onboarding_agent";

// ── Demo chat ──────────────────────────────────────────────────────────────

function DemoChat() {
  return (
    <div className="w-full max-w-2xl border border-border bg-surface-elevated overflow-hidden">
      {/* Title bar */}
      <div className="flex items-center gap-2 px-4 py-2.5 bg-surface border-b border-border">
        <RiTerminalBoxFill size={14} className="text-text-muted shrink-0" />
        <span className="text-xs font-mono text-text-muted">
          vercel/next.js
        </span>
      </div>

      {/* Messages */}
      <div className="flex flex-col gap-6 p-6">
        {/* Turn 1 */}
        <div className="flex justify-end">
          <div className="bg-surface-high border border-border text-text text-sm px-4 py-2.5 max-w-xs leading-relaxed">
            What does this codebase do?
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <span className="text-xs uppercase tracking-widest text-text-subtle">
            Agent
          </span>
          <div className="text-sm text-text leading-relaxed flex flex-col gap-3">
            <p className="text-text-muted">
              This is the{" "}
              <span className="font-mono text-text bg-surface-raised border border-border px-1.5 py-0.5">
                next.js
              </span>{" "}
              monorepo — the React framework that powers millions of production
              apps. Its core responsibility is compiling, routing, and serving
              React applications with both server-side and client-side
              rendering.
            </p>
            <p className="text-text-subtle text-xs font-mono">
              Key areas: packages/next/ · packages/create-next-app/ ·
              packages/next-swc/
            </p>
          </div>
        </div>

        <hr className="border-none h-px bg-border" />

        {/* Turn 2 */}
        <div className="flex justify-end">
          <div className="bg-surface-high border border-border text-text text-sm px-4 py-2.5 max-w-xs leading-relaxed">
            How does the file-system router work?
          </div>
        </div>

        <div className="flex flex-col gap-2">
          <span className="text-xs uppercase tracking-widest text-text-subtle">
            Agent
          </span>
          <div className="text-sm text-text leading-relaxed flex flex-col gap-3">
            <p className="text-text-muted">
              Next.js maps every file inside{" "}
              <span className="font-mono text-text bg-surface-raised border border-border px-1.5 py-0.5">
                app/
              </span>{" "}
              (or{" "}
              <span className="font-mono text-text bg-surface-raised border border-border px-1.5 py-0.5">
                pages/
              </span>
              ) to a URL segment. The router is resolved at build time by{" "}
              <span className="font-mono text-text bg-surface-raised border border-border px-1.5 py-0.5">
                collectAppConfig
              </span>{" "}
              and handed to the server at runtime:
            </p>
            <pre className="bg-surface border border-border p-3 text-xs font-mono text-text-muted overflow-x-auto">
              <code>{`// packages/next/src/server/app-render/app-render.tsx
async function renderToHTMLOrFlight(req, res, pathname) {
  const appConfig  = await collectAppConfig(pathname);
  const components = await resolveComponents(appConfig);
  return renderHTML(components, req, res);
}`}</code>
            </pre>
            <p className="text-text-subtle text-xs">
              Each segment can export{" "}
              <span className="font-mono">layout.tsx</span>,{" "}
              <span className="font-mono">page.tsx</span>, or{" "}
              <span className="font-mono">loading.tsx</span> — the router
              composes them into a nested component tree automatically.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Step card ──────────────────────────────────────────────────────────────

function Step({ number, title, description }) {
  return (
    <div className="flex-1 flex flex-col gap-3 p-6 border border-border bg-surface-elevated">
      <span className="text-xs font-mono text-text-subtle">
        {String(number).padStart(2, "0")}
      </span>
      <h3 className="text-[1rem] font-semibold text-text">{title}</h3>
      <p className="text-sm text-text-muted leading-relaxed">{description}</p>
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-base flex flex-col">
      {/* Nav */}
      <nav className="w-full border-b border-border px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <RiTerminalBoxFill size={18} className="text-text" />
          <span className="text-sm font-semibold text-text tracking-tight">
            Codebase Onboarding Agent
          </span>
        </div>
        <a
          href={REPO_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 text-xs text-text-muted hover:text-text transition-colors duration-150"
        >
          <RiGithubFill size={15} />
          <span className="hidden sm:inline">
            jonehayd/codebase_onboarding_agent
          </span>
        </a>
      </nav>

      {/* Hero */}
      <section className="flex flex-col items-center justify-center text-center px-6 pt-24 pb-20 gap-8">
        <div className="flex flex-col items-center gap-4 max-w-2xl">
          <p className="text-xs uppercase tracking-widest text-text-subtle">
            AI-powered developer onboarding
          </p>
          <h1 className="text-4xl sm:text-5xl font-semibold text-text leading-tight tracking-tight">
            Chat with any{" "}
            <span
              className="font-mono"
              style={{ color: "var(--color-text-muted)" }}
            >
              GitHub
            </span>{" "}
            repository
          </h1>
          <p className="text-[1rem] text-text-muted max-w-lg leading-relaxed">
            Connect a repo and ask questions in plain English. The agent indexes
            your codebase with vector embeddings and answers with precise file
            references and code snippets — no docs required.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-center gap-3">
          <Link
            to="/login"
            className="flex items-center gap-2 px-8 py-3 bg-text text-black text-sm font-semibold uppercase tracking-widest hover:bg-text-muted transition-colors duration-150"
          >
            Get Started
            <LuChevronsRight size={16} />
          </Link>
          <a
            href={REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-8 py-3 border border-border text-sm text-text-muted hover:text-text hover:border-text-subtle transition-colors duration-150"
          >
            <RiGithubFill size={15} />
            View on GitHub
          </a>
        </div>
      </section>

      {/* How it works */}
      <section className="px-6 pb-20 flex flex-col items-center gap-8 max-w-4xl w-full mx-auto">
        <p className="text-xs uppercase tracking-widest text-text-subtle">
          How it works
        </p>
        <div className="w-full flex flex-col sm:flex-row gap-4">
          <Step
            number={1}
            title="Connect a repository"
            description="Sign in with GitHub and paste any public repo URL. The agent fetches every source file and builds a searchable vector index."
          />
          <Step
            number={2}
            title="Ask anything"
            description="Type a question in plain English — about architecture, a specific function, an unfamiliar pattern, or how two modules relate."
          />
          <Step
            number={3}
            title="Get precise answers"
            description="Responses include exact file paths, line references, and code snippets pulled directly from the indexed codebase."
          />
        </div>
      </section>

      {/* Demo chat */}
      <section className="px-6 pb-24 flex flex-col items-center gap-8">
        <p className="text-xs uppercase tracking-widest text-text-subtle">
          See it in action
        </p>
        <DemoChat />
      </section>

      {/* Footer */}
      <footer className="mt-auto border-t border-border px-6 py-6 flex flex-col sm:flex-row items-center justify-between gap-3">
        <span className="text-xs text-text-subtle">
          Codebase Onboarding Agent
        </span>
        <div className="flex items-center gap-4">
          <a
            href={REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-text-subtle hover:text-text-muted transition-colors duration-150 flex items-center gap-1.5"
          >
            <RiGithubFill size={12} />
            GitHub
          </a>
          <Link
            to="/login"
            className="text-xs text-text-subtle hover:text-text-muted transition-colors duration-150"
          >
            Sign in
          </Link>
        </div>
      </footer>
    </div>
  );
}
