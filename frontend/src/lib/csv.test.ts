import { afterEach, describe, expect, it, vi } from "vitest";

import { apiCsvUrl, downloadCsv, toCsv } from "../lib/csv";

type Row = { name: string; value: number | null; note?: string };

describe("toCsv", () => {
  it("writes a header and CRLF-separated rows", () => {
    const columns = [
      { header: "Name", value: (row: Row) => row.name },
      { header: "Value", value: (row: Row) => row.value },
    ];
    expect(toCsv([{ name: "Wind", value: 12 }, { name: "Solar", value: null }], columns)).toBe(
      "Name,Value\r\nWind,12\r\nSolar,",
    );
  });

  it("quotes commas, quotes and newlines and preserves booleans", () => {
    const columns = [
      { header: "Note", value: (row: Row) => row.note },
      { header: "Value", value: (row: Row) => row.value },
      { header: "Done", value: () => true },
    ];
    const csv = toCsv([{ name: "x", value: 1, note: 'a,b "quoted"\nnext' }], columns);
    expect(csv).toContain('"a,b ""quoted""\nnext"');
    expect(csv).toContain(",true");
  });
});

describe("apiCsvUrl", () => {
  it("drops empty parameters and encodes the rest deterministically", () => {
    expect(
      apiCsvUrl("/api/v1/export/accuracy.csv", {
        table: "daily",
        start: "2026-01-02",
        end: undefined,
        cutoff: "09:00",
        empty: "",
      }),
    ).toBe("/api/v1/export/accuracy.csv?table=daily&start=2026-01-02&cutoff=09%3A00");
  });

  it("returns a bare path when no parameters survive", () => {
    expect(apiCsvUrl("/x", { a: undefined, b: "" })).toBe("/x");
  });
});

describe("downloadCsv", () => {
  afterEach(() => vi.restoreAllMocks());

  it("creates an object URL, clicks an anchor and revokes the URL", () => {
    const createObjectURL = vi.fn(() => "blob:windlens");
    const revokeObjectURL = vi.fn();
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: createObjectURL });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: revokeObjectURL });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});

    downloadCsv("wind.csv", "a,b\r\n1,2");

    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(click).toHaveBeenCalledOnce();
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:windlens");
    expect(document.querySelector("a")).toBeNull();
  });
});
