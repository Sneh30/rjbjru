import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ChartFrame } from "./ChartFrame";
import { DataTable, type DataColumn } from "./DataTable";
import { ErrorBoundary } from "./ErrorBoundary";
import { InfoTip } from "./InfoTip";
import { MethodologyDialog } from "./MethodologyDialog";
import { EmptyState, PageSkeleton, Skeleton } from "./States";

type Row = { name: string; value: number | null };

const rows: Row[] = [
  { name: "Bravo", value: 12 },
  { name: "Alpha", value: null },
  { name: "Charlie", value: 3 },
];

const columns: DataColumn<Row>[] = [
  { key: "name", header: "Name", render: (row) => row.name, sortValue: (row) => row.name },
  {
    key: "value",
    header: "Value",
    align: "right",
    render: (row) => String(row.value ?? "—"),
    sortValue: (row) => row.value,
  },
  { key: "static", header: "Note", render: () => "fixed" },
];

describe("DataTable", () => {
  it("renders a caption, rows and non-sortable headers", () => {
    render(
      <DataTable rows={rows} columns={columns} caption="Test table" rowKey={(row) => row.name} />,
    );
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByText("Test table")).toBeInTheDocument();
    expect(screen.getAllByRole("row")).toHaveLength(4);
    expect(screen.getByRole("columnheader", { name: "Note" })).not.toHaveAttribute("aria-sort");
    expect(screen.getByRole("columnheader", { name: /Value/ })).toHaveAttribute("aria-sort", "none");
  });

  it("sorts text and numbers in both directions, keeping nulls last ascending", async () => {
    const user = userEvent.setup();
    render(
      <DataTable
        rows={rows}
        columns={columns}
        caption="Sortable table"
        rowKey={(row) => row.name}
        initialSort={{ key: "name", direction: "desc" }}
      />,
    );
    const bodyRows = () => within(screen.getByRole("table")).getAllByRole("row").slice(1);
    expect(bodyRows().map((row) => row.textContent)).toEqual([
      "Charlie3fixed",
      "Bravo12fixed",
      "Alpha—fixed",
    ]);

    const nameHeader = screen.getByRole("columnheader", { name: /Name/ });
    expect(nameHeader).toHaveAttribute("aria-sort", "descending");
    await user.click(screen.getByRole("button", { name: /Name/ }));
    expect(bodyRows().map((row) => row.textContent)).toEqual([
      "Alpha—fixed",
      "Bravo12fixed",
      "Charlie3fixed",
    ]);
    await user.click(screen.getByRole("button", { name: /Value/ }));
    expect(bodyRows()[0]?.textContent).toBe("Charlie3fixed");
    await user.click(screen.getByRole("button", { name: /Value/ }));
    expect(bodyRows()[0]?.textContent).toBe("Bravo12fixed");
  });

  it("shows an empty message instead of an empty table", () => {
    render(
      <DataTable
        rows={[]}
        columns={columns}
        caption="Empty table"
        rowKey={() => "none"}
        emptyMessage="Nothing here."
      />,
    );
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.getByText("Nothing here.")).toBeInTheDocument();
  });
});

describe("ChartFrame", () => {
  it("toggles its accessible data table", async () => {
    const user = userEvent.setup();
    render(
      <ChartFrame
        title="Chart title"
        insight="What the chart says."
        description="A test chart"
        table={<DataTable rows={rows} columns={columns} caption="Chart table" rowKey={(r) => r.name} />}
      >
        <div>plot</div>
      </ChartFrame>,
    );
    expect(screen.getByRole("heading", { name: "Chart title" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "A test chart" })).toBeInTheDocument();
    const toggle = screen.getByRole("button", { name: "View as table" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    await user.click(toggle);
    expect(screen.getByRole("button", { name: "Hide table" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
    expect(screen.getByRole("table")).toBeInTheDocument();
  });
});

describe("InfoTip", () => {
  it("opens on hover and focus, toggles on click and closes on blur", async () => {
    const user = userEvent.setup();
    render(<InfoTip label="MAE">Mean absolute error</InfoTip>);
    const button = screen.getByRole("button", { name: "MAE: definition" });
    expect(screen.getByRole("tooltip")).toHaveClass("hidden");
    await user.hover(button);
    expect(button).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("tooltip")).toHaveClass("block");
    await user.unhover(button);
    expect(button).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(button);
    expect(button).toHaveAttribute("aria-expanded", "true");
    fireEvent.focus(button);
    fireEvent.blur(button);
    expect(button).toHaveAttribute("aria-expanded", "false");
  });
});

describe("MethodologyDialog", () => {
  function Harness() {
    const [open, setOpen] = useState(false);
    return (
      <>
        <button onClick={() => setOpen(true)}>Open methods</button>
        <MethodologyDialog open={open} onClose={() => setOpen(false)} />
      </>
    );
  }

  it("opens, traps Escape, closes and restores focus", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Harness />
      </MemoryRouter>,
    );
    const trigger = screen.getByRole("button", { name: "Open methods" });
    await user.click(trigger);
    expect(screen.getByRole("dialog", { name: "What WindLens measures" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Close methodology" })).toHaveFocus();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it("closes on the backdrop but not on panel clicks", () => {
    const onClose = vi.fn();
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <MethodologyDialog open onClose={onClose} />
      </MemoryRouter>,
    );
    const dialog = screen.getByRole("dialog");
    fireEvent.mouseDown(dialog);
    expect(onClose).not.toHaveBeenCalled();
    fireEvent.mouseDown(dialog.parentElement as HTMLElement);
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("closes from the footer button", async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <MethodologyDialog open onClose={onClose} />
      </MemoryRouter>,
    );
    await user.click(screen.getByRole("button", { name: "Back to the desk" }));
    expect(onClose).toHaveBeenCalled();
  });
});

describe("ErrorBoundary", () => {
  function Broken(): never {
    throw new Error("synthetic render failure");
  }

  it("shows a recoverable render error", () => {
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <ErrorBoundary>
        <Broken />
      </ErrorBoundary>,
    );
    expect(screen.getByRole("heading", { name: "This view could not be drawn" })).toBeInTheDocument();
    expect(screen.getByText("synthetic render failure")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reload WindLens" })).toBeInTheDocument();
    consoleError.mockRestore();
  });
});

describe("loading and empty states", () => {
  it("exposes skeleton status text", () => {
    render(
      <>
        <Skeleton label="Loading one thing" />
        <PageSkeleton label="Loading the page" />
      </>,
    );
    expect(screen.getByText("Loading one thing")).toBeInTheDocument();
    expect(screen.getByText("Loading the page")).toBeInTheDocument();
  });

  it("renders an empty state with an action", () => {
    render(
      <EmptyState
        title="No rows"
        message="Nothing was published."
        action={<button>Retry</button>}
      />,
    );
    expect(screen.getByText("No observations")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "No rows" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});
