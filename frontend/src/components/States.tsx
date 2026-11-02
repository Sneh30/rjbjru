import type { ReactNode } from "react";

export function Skeleton({ className = "", label }: { className?: string; label?: string }) {
  return (
    <div
      aria-busy="true"
      aria-live="polite"
      className={`skeleton ${className}`}
      role="status"
    >
      <span className="sr-only">{label ?? "Loading"}</span>
    </div>
  );
}

export function PageSkeleton({ label = "Loading this view" }: { label?: string }) {
  return (
    <div className="space-y-4" role="status" aria-live="polite">
      <Skeleton className="h-9 w-72" label={label} />
      <Skeleton className="h-5 w-full max-w-2xl" />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }, (_, index) => (
          <Skeleton key={index} className="h-28" />
        ))}
      </div>
      <Skeleton className="h-[22rem]" />
    </div>
  );
}

export function EmptyState({
  title,
  message,
  action,
}: {
  title: string;
  message: string;
  action?: ReactNode;
}) {
  return (
    <div className="card flex flex-col items-start gap-3 p-8" role="status">
      <span className="chip">No observations</span>
      <h2 className="text-2xl">{title}</h2>
      <p className="max-w-2xl text-soft">{message}</p>
      {action}
    </div>
  );
}

export function ErrorState({
  title = "Could not load this view",
  message,
  onRetry,
}: {
  title?: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="card border-l-4 p-6" role="alert" style={{ borderLeftColor: "var(--over)" }}>
      <p className="eyebrow">Request failed</p>
      <h2 className="mt-1 text-2xl">{title}</h2>
      <p className="mt-2 max-w-2xl text-soft">{message}</p>
      <div className="mt-4 flex flex-wrap gap-2">
        {onRetry ? (
          <button className="btn" onClick={onRetry}>
            Try again
          </button>
        ) : null}
        <a className="btn btn-ghost" href="/api/docs">
          Open API docs
        </a>
      </div>
    </div>
  );
}
