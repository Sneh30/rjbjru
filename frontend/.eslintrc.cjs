module.exports = {
  root: true,
  env: { browser: true, es2022: true },
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react-hooks/recommended",
    "plugin:jsx-a11y/recommended",
  ],
  ignorePatterns: ["dist", "coverage", "playwright-report", "node_modules", "src/**/*.d.ts"],
  parser: "@typescript-eslint/parser",
  parserOptions: { ecmaVersion: "latest", sourceType: "module" },
  plugins: ["@typescript-eslint", "react-refresh"],
  rules: {
    "no-unused-vars": "off",
    "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
    "@typescript-eslint/no-explicit-any": "error",
    "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
    "jsx-a11y/no-autofocus": "off",
    "jsx-a11y/no-noninteractive-tabindex": [
      "error",
      { tags: [], roles: ["region"], allowExpressionValues: true }
    ]
  },
  overrides: [
    {
      files: ["src/**/*.test.{ts,tsx}", "src/test/**", "e2e/**"],
      env: { node: true },
      rules: { "jsx-a11y/aria-role": "off" },
    },
  ],
};
