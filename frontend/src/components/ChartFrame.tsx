import { useState, type ReactNode } from "react";

export function ChartFrame({
  id,
  title,
  insight,
  description,
  actions,
  children,
  table,
  footnote,
}: {
  id?: string;
  title: string;
  insight?: string;
  description: string;
  actions?: ReactNode;
  children: ReactNode;
  table?: ReactNode;
  footnote?: string;
}) {
  const [showTable, setShowTable] = useState(false);
  return (
    <figure className="card p-4 sm:p-5" aria-labelledby={id ? `${id}-title` : undefined}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold" id={id ? `${id}-title` : undefined}>
            {title}
          </h2>
          {insight ? <p className="mt-1 max-w-3xl text-sm text-soft">{insight}</p> : null}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {actions}
          {table ? (
            <button
              type="button"
              className="btn btn-ghost text-xs"
              aria-expanded={showTable}
              onClick={() => setShowTable((value) => !value)}
            >
              {showTable ? "Hide table" : "View as table"}
            </button>
          ) : null}
        </div>
      </div>
      <p className="sr-only">{description}</p>
      <div className="mt-4" role="img" aria-label={description}>
        {children}
      </div>
      {showTable ? <div className="mt-4">{table}</div> : null}
      {footnote ? <figcaption className="mt-3 text-xs text-muted">{footnote}</figcaption> : null}
    </figure>
  );
}
