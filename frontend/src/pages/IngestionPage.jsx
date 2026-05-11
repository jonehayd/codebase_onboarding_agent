import { useState, useEffect, useCallback } from "react";
import { useParams } from "react-router-dom";
import {
  getSessionDetail,
  getSessionStatus,
  cancelIngestion,
  retryIngestion,
} from "@api/sessions";

const STAGES = [
  { key: "fetching_files", label: "Fetching all files" },
  { key: "parsing_code", label: "Parsing code" },
  { key: "generating_embeddings", label: "Generating embeddings" },
];

const ACTIVE_STATUSES = new Set(["pending", "processing"]);

function formatElapsed(seconds) {
  if (seconds == null) return "--:--";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function formatCount(n) {
  if (n == null) return "-";
  return n.toLocaleString();
}

// --- Sub-components ---

function CircularProgress({ percent, isComplete, isFailed }) {
  const r = 52;
  const circ = 2 * Math.PI * r;
  const offset = circ - (percent / 100) * circ;
  const strokeColor = isFailed
    ? "var(--color-error)"
    : isComplete
      ? "var(--color-success)"
      : "var(--color-text)";

  return (
    <div
      className="relative inline-flex items-center justify-center"
      style={{ width: 144, height: 144 }}
    >
      <svg
        width="144"
        height="144"
        viewBox="0 0 144 144"
        style={{ transform: "rotate(-90deg)" }}
      >
        <circle
          cx="72"
          cy="72"
          r={r}
          fill="none"
          stroke="var(--color-surface-high)"
          strokeWidth="10"
        />
        <circle
          cx="72"
          cy="72"
          r={r}
          fill="none"
          stroke={strokeColor}
          strokeWidth="10"
          strokeLinecap="butt"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          style={{
            transition: "stroke-dashoffset 0.5s ease, stroke 0.3s ease",
          }}
        />
      </svg>
      <span
        className="absolute text-2xl font-semibold"
        style={{ color: strokeColor, transition: "color 0.3s ease" }}
      >
        {percent}%
      </span>
    </div>
  );
}

function CheckIcon() {
  return (
    <svg width="10" height="8" viewBox="0 0 10 8" fill="none">
      <path
        d="M1 4L3.5 6.5L9 1"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function SpinnerDot() {
  return (
    <span
      className="block w-2 h-2 rounded-full bg-text"
      style={{ animation: "pulse 1.2s ease-in-out infinite" }}
    />
  );
}

function ChecklistItem({ stageKey, currentStage, isComplete }) {
  const stageIdx = STAGES.findIndex((s) => s.key === stageKey);
  const currentIdx = STAGES.findIndex((s) => s.key === currentStage);
  const isDone = isComplete || stageIdx < currentIdx;
  const isActive = !isComplete && stageIdx === currentIdx;
  const label = STAGES[stageIdx].label;

  let textClass = "text-text-subtle";
  if (isDone) textClass = "text-success";
  else if (isActive) textClass = "text-text";

  return (
    <div className={`flex items-center gap-3 text-sm ${textClass}`}>
      <div
        className="w-5 h-5 border flex items-center justify-center shrink-0"
        style={{
          borderColor: isDone
            ? "var(--color-success)"
            : isActive
              ? "var(--color-text)"
              : "var(--color-surface-highest)",
          backgroundColor: isDone ? "var(--color-success)" : "transparent",
        }}
      >
        {isDone && <CheckIcon />}
        {isActive && <SpinnerDot />}
      </div>
      <span>{label}</span>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="flex flex-col items-center gap-1">
      <span className="text-xs uppercase tracking-widest text-text-subtle">
        {label}
      </span>
      <span className="text-lg font-mono text-text">{value}</span>
    </div>
  );
}

// --- Main view (embeddable — accepts sessionId as a prop) ---

export function IngestionView({ sessionId }) {
  const [session, setSession] = useState(null);
  const [status, setStatus] = useState(null);
  const [cancelling, setCancelling] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [fetchError, setFetchError] = useState(null);

  // Load repo name once
  useEffect(() => {
    getSessionDetail(sessionId)
      .then(setSession)
      .catch(() => {});
  }, [sessionId]);

  // Poll ingestion status
  useEffect(() => {
    let active = true;
    let intervalId;

    const poll = async () => {
      try {
        const data = await getSessionStatus(sessionId);
        if (!active) return;
        setStatus(data);
        setFetchError(null);
        if (!ACTIVE_STATUSES.has(data.status)) {
          clearInterval(intervalId);
        }
      } catch (e) {
        if (active) setFetchError(e.message);
      }
    };

    poll();
    intervalId = setInterval(poll, 2000);

    return () => {
      active = false;
      clearInterval(intervalId);
    };
  }, [sessionId]);

  const handleCancel = useCallback(async () => {
    setCancelling(true);
    try {
      await cancelIngestion(sessionId);
    } catch {
      setCancelling(false);
    }
  }, [sessionId]);

  const handleRetry = useCallback(async () => {
    setRetrying(true);
    try {
      await retryIngestion(sessionId);
      setRetrying(false);
      // Resume polling
      setStatus((prev) =>
        prev
          ? { ...prev, status: "pending", stage: "fetching_files", percent: 0 }
          : prev,
      );
    } catch {
      setRetrying(false);
    }
  }, [sessionId]);

  const repoLabel = session
    ? `${session.repo.owner}/${session.repo.name}`
    : "Loading…";

  const isActive = status && ACTIVE_STATUSES.has(status.status);
  const isComplete = status?.status === "completed";
  const isFailed = status?.status === "failed";
  const isCancelled = status?.stage === "cancelled";

  const percent = status?.percent ?? 0;
  const currentStage = status?.stage ?? "fetching_files";

  return (
    <div className="min-h-screen bg-base flex flex-col items-center justify-center p-8">
      <div className="w-full max-w-sm flex flex-col items-center gap-8">
        {/* Header */}
        <div className="text-center">
          <p className="text-xs uppercase tracking-widest text-text-subtle mb-1">
            {isComplete
              ? "Ingestion complete"
              : isCancelled
                ? "Ingestion cancelled"
                : isFailed
                  ? "Ingestion failed"
                  : "Ingesting repository"}
          </p>
          <h1 className="text-xl font-semibold text-text font-mono">
            {repoLabel}
          </h1>
        </div>

        {/* Circular progress */}
        <CircularProgress
          percent={percent}
          isComplete={isComplete}
          isFailed={isFailed && !isCancelled}
        />

        {/* Stage label */}
        <p className="text-sm text-text-muted -mt-4">
          {isComplete
            ? "All files indexed successfully"
            : isCancelled
              ? "Cancelled by user"
              : isFailed
                ? "An error occurred during ingestion"
                : currentStage === "fetching_files"
                  ? "Fetching repository files…"
                  : currentStage === "parsing_code"
                    ? "Parsing source code…"
                    : currentStage === "generating_embeddings"
                      ? "Generating embeddings…"
                      : "Preparing…"}
        </p>

        {/* Checklist */}
        <div className="w-full flex flex-col gap-3 px-1">
          {STAGES.map((s) => (
            <ChecklistItem
              key={s.key}
              stageKey={s.key}
              currentStage={currentStage}
              isComplete={isComplete}
            />
          ))}
        </div>

        {/* Divider */}
        <hr className="w-full border-none h-px bg-border" />

        {/* Stats */}
        <div className="w-full grid grid-cols-3 gap-4">
          <Stat label="Files" value={formatCount(status?.file_count)} />
          <Stat label="Vectors" value={formatCount(status?.vector_count)} />
          <Stat
            label="Elapsed"
            value={formatElapsed(status?.elapsed_seconds)}
          />
        </div>

        {/* Actions */}
        {fetchError && (
          <p className="text-xs text-error text-center">{fetchError}</p>
        )}

        {isActive && (
          <button
            onClick={handleCancel}
            disabled={cancelling}
            className="w-full py-3 border border-error text-error text-sm font-semibold uppercase tracking-widest cursor-pointer hover:bg-error-bg transition-colors duration-150 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {cancelling ? "Cancelling…" : "Cancel Ingestion"}
          </button>
        )}

        {(isFailed || isCancelled) && (
          <button
            onClick={handleRetry}
            disabled={retrying}
            className="w-full py-3 bg-text text-black text-sm font-semibold uppercase tracking-widest cursor-pointer hover:bg-text-muted transition-colors duration-150 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {retrying ? "Retrying…" : "Retry Ingestion"}
          </button>
        )}
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </div>
  );
}

// --- Router page wrapper ---

export default function IngestionPage() {
  const { sessionId } = useParams();
  return <IngestionView sessionId={sessionId} />;
}
