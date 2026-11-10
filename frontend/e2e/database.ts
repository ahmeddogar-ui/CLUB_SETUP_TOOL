import { execFileSync } from "node:child_process";

export const E2E_DATABASE_URL =
  process.env.E2E_DATABASE_URL ??
  "postgresql://localhost:5432/club_setup_tool_e2e_test";

/** There is no API for granting the admin role, so do what an operator would. */
export function promoteToAdmin(email: string) {
  // Variables are only interpolated in SQL read from stdin, not from --command.
  const output = execFileSync(
    "psql",
    [E2E_DATABASE_URL, "--set=ON_ERROR_STOP=1", "--set", `email=${email}`],
    {
      input: "UPDATE users SET role = 'admin' WHERE email = :'email';",
      encoding: "utf8",
    },
  );
  if (!output.includes("UPDATE 1")) {
    throw new Error(`Expected to promote one user (${email}), got: ${output}`);
  }
}
