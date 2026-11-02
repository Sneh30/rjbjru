import { Component, type ErrorInfo, type ReactNode } from "react";

type Props = { children: ReactNode };
type State = { error: Error | null };

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("WindLens render error", error, info.componentStack);
  }

  render(): ReactNode {
    if (this.state.error) {
      return (
        <main className="wrap py-16" id="main">
          <div className="card mx-auto max-w-xl p-8">
            <p className="eyebrow">Render error</p>
            <h1 className="mt-2 text-3xl">This view could not be drawn</h1>
            <p className="mt-3 text-soft">
              The data request may have succeeded but a component failed. Reload the page to
              retry; the snapshot itself is unaffected.
            </p>
            <pre className="mt-4 overflow-auto rounded-lg bg-sunken p-3 text-xs">
              {this.state.error.message}
            </pre>
            <button className="btn btn-primary mt-5" onClick={() => window.location.reload()}>
              Reload WindLens
            </button>
          </div>
        </main>
      );
    }
    return this.props.children;
  }
}
