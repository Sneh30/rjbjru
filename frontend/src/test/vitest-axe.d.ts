import type { AxeMatchers } from "vitest-axe";

import "vitest";

declare module "vitest" {
  // Vitest's own declaration uses `any` here, so the default must match to merge.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  interface Assertion<T = any> extends AxeMatchers {}
  interface AsymmetricMatchersContaining extends AxeMatchers {}
}
