import { execFileSync } from "node:child_process";

/** Environment for every backend process the e2e run starts. */
export const BACKEND_ENV = {
  DATABASE_URL:
    process.env.E2E_DATABASE_URL ??
    "postgresql://localhost:5432/club_setup_tool_e2e_test",
  SECRET_KEY: "e2e-secret-key-not-used-anywhere-else-32b",
};

/** There is no API for granting the admin role; use the operator command. */
export function makeAdmin(email: string) {
  execFileSync("uv", ["run", "python", "-m", "app.cli", "make-admin", email], {
    cwd: "..",
    env: { ...process.env, ...BACKEND_ENV },
  });
}
