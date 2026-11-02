import { useId, useState } from "react";

export function InfoTip({ label, children }: { label: string; children: string }) {
  const id = useId();
  const [open, setOpen] = useState(false);
  return (
    <span className="relative inline-flex align-middle">
      <button
        type="button"
        className="inline-flex h-5 w-5 items-center justify-center rounded-full border text-[11px] font-bold text-muted"
        aria-label={`${label}: definition`}
        aria-describedby={open ? id : undefined}
        aria-expanded={open}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={() => setOpen((value) => !value)}
        style={{ borderColor: "var(--rule-strong)" }}
      >
        i
      </button>
      <span
        id={id}
        role="tooltip"
        className={`chart-tooltip absolute left-1/2 top-7 z-30 w-64 -translate-x-1/2 ${
          open ? "block" : "hidden"
        }`}
      >
        {children}
      </span>
    </span>
  );
}
