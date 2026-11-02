import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";

export function MethodologyDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
      if (event.key !== "Tab" || !panelRef.current) return;
      const focusable = panelRef.current.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), input, select, textarea, [tabindex]:not([tabindex="-1"])',
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = overflow;
      previous?.focus();
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      role="presentation"
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto p-4 sm:p-8"
      style={{ background: "rgba(10, 15, 20, 0.56)" }}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="methodology-title"
        className="card my-8 w-full max-w-2xl p-5 sm:p-7"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="eyebrow">Methods in brief</p>
            <h2 className="mt-1 text-3xl" id="methodology-title">
              What WindLens measures
            </h2>
          </div>
          <button ref={closeRef} className="btn btn-ghost" onClick={onClose} aria-label="Close methodology">
            Close
          </button>
        </div>
        <div className="prose-wind mt-4 text-sm">
          <p>
            For delivery day <em>D</em>, the cutoff is <strong>09:00 Europe/London on D−1</strong>.
            Each hour uses the <strong>latest WINDFOR vintage published at or before that cutoff</strong>,
            so no post-cutoff information can leak into the decision view. Horizon is target time
            minus publish time.
          </p>
          <p>
            Actuals are FUELHH WIND settlement periods averaged into London hours; the ordinary
            mean of the two half-hours is used and missing pairs are excluded, never imputed. Error
            is <strong>forecast − actual</strong>: positive means over-forecast and shortfall risk.
          </p>
          <p>
            The risk buffer is the empirical signed-error quantile. The walk-forward back-test only
            uses outcomes known two days before each evaluated delivery day. It is evidence about a
            31-day window, not a guarantee.
          </p>
          <ul>
            <li>No demand, price, weather, capacity or other fuel data is used.</li>
            <li>nMAE is MAE divided by mean actual; MAPE is guarded at 500 MW actual.</li>
            <li>Persistence holds the last complete actual known at the cutoff flat.</li>
            <li>Scatter plots use a deterministic sample when the window is large.</li>
          </ul>
        </div>
        <div className="mt-5 flex flex-wrap gap-2">
          <Link className="btn btn-primary" to="/about" onClick={onClose}>
            Full methodology
          </Link>
          <a className="btn" href="/api/docs">
            API reference
          </a>
          <button className="btn btn-ghost" onClick={onClose}>
            Back to the desk
          </button>
        </div>
      </div>
    </div>
  );
}
