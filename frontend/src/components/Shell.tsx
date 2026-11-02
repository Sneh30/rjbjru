import { useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";

import { useMeta } from "../api/hooks";
import { formatDateTime, shortHash } from "../lib/format";
import { MethodologyDialog } from "./MethodologyDialog";
import { ErrorBoundary } from "./ErrorBoundary";

const NAV = [
  { to: "/desk", label: "Decision Desk", short: "Desk" },
  { to: "/lab", label: "Accuracy Lab", short: "Lab" },
  { to: "/revisions", label: "Revisions", short: "Revisions" },
  { to: "/about", label: "About", short: "About" },
];

function BrandMark() {
  return (
    <svg aria-hidden="true" viewBox="0 0 40 40" className="h-9 w-9" fill="none">
      <circle cx="20" cy="20" r="18" stroke="currentColor" strokeWidth="1.4" opacity="0.45" />
      <circle cx="20" cy="20" r="4" fill="currentColor" />
      <path d="M20 4v9M20 27v9M4 20h9M27 20h9" stroke="currentColor" strokeWidth="1.4" />
      <path d="M9 9l5 5M26 26l5 5M31 9l-5 5M14 26l-5 5" stroke="currentColor" strokeWidth="1" opacity="0.5" />
    </svg>
  );
}

function TopNav() {
  return (
    <nav aria-label="Primary" className="flex items-center gap-1 overflow-x-auto">
      {NAV.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) =>
            `whitespace-nowrap rounded-lg px-2.5 py-2 text-sm font-medium transition-colors sm:px-3 ${
              isActive ? "bg-sunken text-ink" : "text-soft hover:bg-sunken hover:text-ink"
            }`
          }
        >
          <span className="hidden sm:inline">{item.label}</span>
          <span className="sm:hidden">{item.short}</span>
        </NavLink>
      ))}
    </nav>
  );
}

function ProvenanceBar() {
  const meta = useMeta();
  const data = meta.data;
  return (
    <footer className="mt-12 border-t" style={{ borderColor: "var(--rule)" }}>
      <div className="wrap flex flex-wrap items-center justify-between gap-x-6 gap-y-1 py-4 text-xs text-muted">
        <p>
          <span className="font-semibold text-soft">Data:</span> Elexon BMRS FUELHH (WIND) &amp;
          WINDFOR
          {data ? (
            <>
              {" "}
              · snapshot ingested {formatDateTime(data.data.generated_at)} · hash{" "}
              <span className="font-mono">{shortHash(data.data.fingerprint)}</span>
            </>
          ) : null}
        </p>
        <p className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <span>Europe/London · MW · 31 delivery days</span>
          <Link className="underline" to="/about#ai">
            AI disclosure
          </Link>
          {meta.isError ? (
            <button className="underline" onClick={() => void meta.refetch()}>
              Metadata unavailable — retry
            </button>
          ) : null}
        </p>
      </div>
    </footer>
  );
}

export function Shell() {
  const meta = useMeta();
  const location = useLocation();
  const [methodologyOpen, setMethodologyOpen] = useState(false);
  const mainRef = useRef<HTMLElement>(null);

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "auto" });
    mainRef.current?.focus({ preventScroll: true });
  }, [location.pathname]);

  return (
    <div className="flex min-h-screen flex-col">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header
        className="border-b backdrop-blur"
        style={{
          borderColor: "var(--rule)",
          background: "color-mix(in srgb, var(--paper-raised) 78%, transparent)",
        }}
      >
        <div className="wrap flex flex-wrap items-center gap-x-5 gap-y-2 py-3">
          <Link to="/desk" className="flex items-center gap-2.5 text-ink">
            <span style={{ color: "var(--forecast)" }}>
              <BrandMark />
            </span>
            <span>
              <span className="block font-display text-2xl leading-none tracking-tight">WindLens</span>
              <span className="mt-0.5 block text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">
                Day-ahead wind desk
              </span>
            </span>
          </Link>
          <div className="order-3 w-full sm:order-none sm:ml-2 sm:w-auto">
            <TopNav />
          </div>
          <div className="ml-auto flex items-center gap-2">
            {meta.data ? (
              <span className="chip hidden md:inline-flex" title="Decision-time wind forecast snapshot">
                <span
                  className="h-1.5 w-1.5 rounded-full"
                  style={{ background: "var(--under)" }}
                  aria-hidden="true"
                />
                Snapshot {shortHash(meta.data.data.fingerprint)}
              </span>
            ) : null}
            <button className="btn btn-ghost text-sm" onClick={() => setMethodologyOpen(true)}>
              Methodology
            </button>
          </div>
        </div>
      </header>

      <main
        id="main"
        ref={mainRef}
        tabIndex={-1}
        className="wrap flex-1 py-6 outline-none sm:py-8"
      >
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
      </main>

      <ProvenanceBar />
      <MethodologyDialog open={methodologyOpen} onClose={() => setMethodologyOpen(false)} />
    </div>
  );
}
