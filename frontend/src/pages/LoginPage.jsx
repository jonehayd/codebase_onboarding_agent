import { RiTerminalBoxFill } from "react-icons/ri";
import Card from "@components/ui/Card";

const GITHUB_OAUTH_URL = `https://github.com/login/oauth/authorize?client_id=${import.meta.env.VITE_GITHUB_CLIENT_ID}&scope=repo,read:user`;

export default function LoginPage() {
  return (
    <div className="min-h-screen bg-color-base flex items-center justify-center px-4">
      <Card className="w-full max-w-150 min-h-150 flex flex-col items-center justify-center gap-4 mx-auto text-center p-8">
        <RiTerminalBoxFill className="w-20 h-20 text-color-text m-4 p-2 border border-border bg-surface-high" />
        <div className="flex flex-col gap-2">
          <h1 className="text-4xl m-2">Codebase Onboarding Agent</h1>
          <p className="text-lg text-text-muted">
            Connect a GitHub repository and get an AI-powered walkthrough of its
            architecture, structure, and key patterns.
          </p>
        </div>

        <hr className="w-full border-none h-px bg-color-border" />

        <GitHubButton href={GITHUB_OAUTH_URL} />
      </Card>
    </div>
  );
}

function GitHubButton({ href }) {
  return (
    <a
      href={href}
      className="inline-flex items-center gap-2 w-full justify-center px-5
        bg-text text-black! font-medium text-sm
        hover:bg-text-muted transition-colors duration-150 py-5 m-4"
    >
      <GitHubIcon />
      Continue with GitHub
    </a>
  );
}

function GitHubIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
      className="shrink-0"
    >
      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0 0 24 12c0-6.63-5.37-12-12-12z" />
    </svg>
  );
}
