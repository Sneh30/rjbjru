import type { AxeResults, RunOptions } from "axe-core";

declare global {
  interface Window {
    axe: {
      run(context?: Document | Element, options?: RunOptions): Promise<AxeResults>;
    };
  }
}

export {};
