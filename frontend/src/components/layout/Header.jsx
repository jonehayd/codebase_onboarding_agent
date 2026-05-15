import { useNavigate } from "react-router-dom";
import ShareButton from "./ShareButton";

export default function Header({ activeSession }) {
  const navigate = useNavigate();

  const handleLogout = () => {
    localStorage.removeItem("token");
    navigate("/"); // landing page
  };

  return (
    <header className="w-full h-16 bg-color-surface flex items-center border-b border-color-border px-4 gap-3">
      <h1 className="text-xl font-semibold text-color-text shrink-0">
        CODEBASE_ONBOARDING_AGENT
      </h1>
      {activeSession?.repoName && (
        <>
          <span className="text-text-subtle select-none">/</span>
          <span className="text-sm font-mono text-text-muted truncate">
            {activeSession.repoName}
          </span>
        </>
      )}
      <div className="ml-auto flex items-center gap-2">
        <ShareButton activeSession={activeSession} />
        <button
          onClick={handleLogout}
          className="px-4 py-2 bg-text text-black font-medium text-sm rounded cursor-pointer hover:bg-text-muted transition-colors duration-150"
        >
          LOGOUT
        </button>
      </div>
    </header>
  );
}
