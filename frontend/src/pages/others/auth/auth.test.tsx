import { TOKEN_KEY } from "@/lib/api";
import { LEAD } from "@/test/builders";
import { renderApp } from "@/test/render-app";
import { server } from "@/test/server";
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

const ISSUED_TOKEN = "issued-token";

function serveClubList() {
  server.use(http.get("/api/clubs", () => HttpResponse.json([])));
}

describe("signing in", () => {
  it("sends the backend's form-encoded login, stores the token and opens the club list", async () => {
    let loginBody: URLSearchParams | undefined;
    server.use(
      http.post("/api/auth/login", async ({ request }) => {
        loginBody = new URLSearchParams(await request.text());
        return HttpResponse.json({
          access_token: ISSUED_TOKEN,
          token_type: "bearer",
        });
      }),
      http.get("/api/auth/me", ({ request }) =>
        request.headers.get("Authorization") === `Bearer ${ISSUED_TOKEN}`
          ? HttpResponse.json(LEAD)
          : new HttpResponse(null, { status: 401 }),
      ),
    );
    serveClubList();
    const { user } = renderApp("/signin");

    await user.type(await screen.findByLabelText(/^email/i), LEAD.email);
    await user.type(screen.getByLabelText(/^password/i), "hunter22");
    await user.click(screen.getByRole("button", { name: "Sign In" }));

    expect(
      await screen.findByRole("heading", { name: "My clubs" }),
    ).toBeInTheDocument();
    expect(loginBody?.get("username")).toBe(LEAD.email);
    expect(loginBody?.get("password")).toBe("hunter22");
    expect(localStorage.getItem(TOKEN_KEY)).toBe(ISSUED_TOKEN);
  });

  it("shows the backend's error and stores nothing when credentials are wrong", async () => {
    server.use(
      http.post("/api/auth/login", () =>
        HttpResponse.json(
          { detail: "Incorrect email or password" },
          { status: 401 },
        ),
      ),
    );
    const { user } = renderApp("/signin");

    await user.type(await screen.findByLabelText(/^email/i), LEAD.email);
    await user.type(screen.getByLabelText(/^password/i), "wrong");
    await user.click(screen.getByRole("button", { name: "Sign In" }));

    expect(
      await screen.findByText("Incorrect email or password"),
    ).toBeInTheDocument();
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
  });

  it("validates the form before calling the backend", async () => {
    // No login handler: an unexpected request fails the test (onUnhandledFrame: "error").
    const { user } = renderApp("/signin");

    await user.type(await screen.findByLabelText(/^email/i), "not-an-email");
    await user.click(screen.getByRole("button", { name: "Sign In" }));

    expect(
      await screen.findByText("Please enter a valid email address"),
    ).toBeInTheDocument();
    expect(screen.getByText("Password is required")).toBeInTheDocument();
  });
});

describe("signing up", () => {
  it("registers with the combined name, then asks the user to sign in", async () => {
    let registered: unknown;
    server.use(
      http.post("/api/auth/register", async ({ request }) => {
        registered = await request.json();
        return HttpResponse.json({ ...LEAD, id: 99 }, { status: 201 });
      }),
    );
    const { user } = renderApp("/signup");

    await user.type(await screen.findByLabelText(/^first name/i), "Lena");
    await user.type(screen.getByLabelText(/^last name/i), "Lead");
    await user.type(screen.getByLabelText(/^email/i), LEAD.email);
    await user.type(screen.getByLabelText(/^password/i), "longenough");
    await user.type(screen.getByLabelText(/^confirm password/i), "longenough");
    await user.click(screen.getByRole("button", { name: "Sign Up" }));

    expect(await screen.findByText("Account created")).toBeInTheDocument();
    expect(registered).toEqual({
      name: "Lena Lead",
      email: LEAD.email,
      password: "longenough",
    });
  });

  it("refuses mismatched passwords without calling the backend", async () => {
    const { user } = renderApp("/signup");

    await user.type(await screen.findByLabelText(/^password/i), "longenough");
    await user.type(screen.getByLabelText(/^confirm password/i), "different1");
    await user.click(screen.getByRole("button", { name: "Sign Up" }));

    expect(
      await screen.findByText("Passwords do not match"),
    ).toBeInTheDocument();
  });
});

describe("route guards", () => {
  it("sends a signed-out visitor to the sign-in page", async () => {
    renderApp("/clubs/10");

    expect(
      await screen.findByRole("heading", { name: "Sign In" }),
    ).toBeInTheDocument();
  });

  it("drops a stored token the backend rejects and shows the sign-in page", async () => {
    localStorage.setItem(TOKEN_KEY, "expired-token");
    server.use(
      http.get("/api/auth/me", () =>
        HttpResponse.json(
          { detail: "Could not validate credentials" },
          { status: 401 },
        ),
      ),
    );
    renderApp("/");

    expect(
      await screen.findByRole("heading", { name: "Sign In" }),
    ).toBeInTheDocument();
    expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
  });

  it("keeps a club lead out of the admin review queue", async () => {
    // Only the lead's own list is served; a request for the queue would fail the test.
    serveClubList();
    renderApp("/review", { signedInAs: LEAD });

    expect(
      await screen.findByRole("heading", { name: "My clubs" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Waiting for review")).not.toBeInTheDocument();
  });
});
