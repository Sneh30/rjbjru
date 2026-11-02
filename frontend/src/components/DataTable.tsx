import { useMemo, useState, type ReactNode } from "react";

export type DataColumn<T> = {
  key: string;
  header: string;
  align?: "left" | "right";
  render: (row: T) => ReactNode;
  sortValue?: (row: T) => string | number | null;
  headerHint?: string;
};

type SortState = { key: string; direction: "asc" | "desc" } | null;

export function DataTable<T>({
  rows,
  columns,
  caption,
  rowKey,
  initialSort,
  emptyMessage = "No rows to show.",
  maxHeight = "26rem",
}: {
  rows: T[];
  columns: DataColumn<T>[];
  caption: string;
  rowKey: (row: T, index: number) => string;
  initialSort?: SortState;
  emptyMessage?: string;
  maxHeight?: string;
}) {
  const [sort, setSort] = useState<SortState>(initialSort ?? null);

  const sorted = useMemo(() => {
    if (!sort) return rows;
    const column = columns.find((candidate) => candidate.key === sort.key);
    if (!column?.sortValue) return rows;
    const copy = [...rows];
    copy.sort((left, right) => {
      const a = column.sortValue?.(left);
      const b = column.sortValue?.(right);
      if (a === null || a === undefined) return 1;
      if (b === null || b === undefined) return -1;
      if (typeof a === "number" && typeof b === "number") {
        return sort.direction === "asc" ? a - b : b - a;
      }
      return sort.direction === "asc"
        ? String(a).localeCompare(String(b), "en-GB")
        : String(b).localeCompare(String(a), "en-GB");
    });
    return copy;
  }, [rows, columns, sort]);

  if (rows.length === 0) {
    return <p className="p-4 text-sm text-muted">{emptyMessage}</p>;
  }

  return (
    <div className="table-wrap" style={{ maxHeight }} tabIndex={0} role="region" aria-label={caption}>
      <table className="data-table">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr>
            {columns.map((column) => {
              const active = sort?.key === column.key;
              const ariaSort = active ? (sort.direction === "asc" ? "ascending" : "descending") : "none";
              return (
                <th
                  key={column.key}
                  scope="col"
                  aria-sort={column.sortValue ? ariaSort : undefined}
                  className={column.align === "right" ? "text-right" : undefined}
                  title={column.headerHint}
                >
                  {column.sortValue ? (
                    <button
                      type="button"
                      className="inline-flex items-center gap-1 font-semibold uppercase tracking-wide hover:underline"
                      onClick={() =>
                        setSort((current) => {
                          if (current?.key !== column.key) {
                            return { key: column.key, direction: "asc" };
                          }
                          return {
                            key: column.key,
                            direction: current.direction === "asc" ? "desc" : "asc",
                          };
                        })
                      }
                    >
                      {column.header}
                      <span aria-hidden="true">{active ? (sort.direction === "asc" ? "↑" : "↓") : "↕"}</span>
                    </button>
                  ) : (
                    column.header
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, index) => (
            <tr key={rowKey(row, index)}>
              {columns.map((column) => (
                <td
                  key={column.key}
                  className={column.align === "right" ? "num" : undefined}
                >
                  {column.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
