import { useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

export default function AuthCallbackPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token");

  useEffect(() => {
    if (!token) return;
    localStorage.setItem("token", token);
    navigate("/app", { replace: true });
  }, [token, navigate]);

  if (!token) {
    return (
      <div className="min-h-screen bg-base flex items-center justify-center">
        <div className="text-center flex flex-col gap-4">
          <p className="text-error">
            Authentication failed — no token received.
          </p>
          <a
            href="/login"
            className="text-text-muted hover:text-text underline text-sm"
          >
            Back to login
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-base flex items-center justify-center">
      <p className="text-text-muted text-sm">Authenticating…</p>
    </div>
  );
}
