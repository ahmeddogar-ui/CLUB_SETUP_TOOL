import { defineConfig, devices } from "@playwright/test";
import { BACKEND_ENV } from "./e2e/backend.ts";

// The e2e run starts its own backend and Vite server on ports that don't clash
// with a dev session, against a dedicated database (migrated on startup).
const API_PORT = 8100;
const WEB_PORT = 5174;
const isCI = Boolean(process.env.CI);

export default defineConfig({
  testDir: "./e2e",
  forbidOnly: isCI,
  retries: isCI ? 1 : 0,
  reporter: isCI ? [["github"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `uv run alembic upgrade head && uv run uvicorn app.main:app --port ${API_PORT}`,
      cwd: "..",
      url: `http://localhost:${API_PORT}/health`,
      env: BACKEND_ENV,
      reuseExistingServer: false,
    },
    {
      command: `npm run dev -- --port ${WEB_PORT} --strictPort`,
      url: `http://localhost:${WEB_PORT}`,
      env: { API_URL: `http://localhost:${API_PORT}` },
      reuseExistingServer: false,
    },
  ],
});
