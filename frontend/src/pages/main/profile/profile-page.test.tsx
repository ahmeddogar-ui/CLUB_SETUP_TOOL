import { LEAD, buildClubPage } from "@/test/builders";
import { renderApp } from "@/test/render-app";
import { server } from "@/test/server";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

const CURRENT_PASSWORD = "current-password";
const NEW_PASSWORD = "brand-new-password";

function openProfile() {
  return renderApp("/profile", { signedInAs: LEAD });
}

async function fillPasswordForm(
  user: ReturnType<typeof openProfile>["user"],
  confirmation = NEW_PASSWORD,
) {
  await user.type(
    await screen.findByLabelText(/^current password/i),
    CURRENT_PASSWORD,
  );
  await user.type(screen.getByLabelText(/^new password/i), NEW_PASSWORD);
  await user.type(
    screen.getByLabelText(/^confirm new password/i),
    confirmation,
  );
  await user.click(screen.getByRole("button", { name: "Change password" }));
}

describe("profile details", () => {
  it("shows the email and role read-only", async () => {
    openProfile();

    expect(await screen.findByText(LEAD.email)).toBeInTheDocument();
    expect(screen.getByText("Club lead")).toBeInTheDocument();
  });

  it("renames the user and confirms with a toast", async () => {
    let sentBody: unknown;
    server.use(
      http.patch("/api/auth/me", async ({ request }) => {
        sentBody = await request.json();
        return HttpResponse.json({ ...LEAD, name: "Lena Renamed" });
      }),
    );
    const { user } = openProfile();

    const nameInput = await screen.findByLabelText(/^name/i);
    await user.clear(nameInput);
    await user.type(nameInput, "Lena Renamed");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    expect(await screen.findByText("Name updated")).toBeInTheDocument();
    expect(sentBody).toEqual({ name: "Lena Renamed" });
  });

  it("refreshes the signed-in user after a rename", async () => {
    server.use(
      http.patch("/api/auth/me", () => {
        server.use(
          http.get("/api/auth/me", () =>
            HttpResponse.json({ ...LEAD, name: "Lena Renamed" }),
          ),
        );
        return HttpResponse.json({ ...LEAD, name: "Lena Renamed" });
      }),
    );
    const { user } = openProfile();

    const nameInput = await screen.findByLabelText(/^name/i);
    await user.clear(nameInput);
    await user.type(nameInput, "Lena Renamed");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    expect(
      await screen.findByRole("button", { name: /lena renamed/i }),
    ).toBeInTheDocument();
  });
});

describe("change password", () => {
  it("refuses mismatched passwords without calling the backend", async () => {
    // No handler for the password endpoint: a request would fail the test.
    const { user } = openProfile();

    await fillPasswordForm(user, "something-else-1");

    expect(
      await screen.findByText("Passwords do not match"),
    ).toBeInTheDocument();
  });

  it("shows the backend's message when the current password is wrong", async () => {
    server.use(
      http.post("/api/auth/me/password", () =>
        HttpResponse.json(
          { detail: "Current password is incorrect" },
          { status: 403 },
        ),
      ),
    );
    const { user } = openProfile();

    await fillPasswordForm(user);

    expect(
      await screen.findByText("Current password is incorrect"),
    ).toBeInTheDocument();
  });

  it("confirms with a toast and clears the fields on success", async () => {
    let sentBody: unknown;
    server.use(
      http.post("/api/auth/me/password", async ({ request }) => {
        sentBody = await request.json();
        return new HttpResponse(null, { status: 204 });
      }),
    );
    const { user } = openProfile();

    await fillPasswordForm(user);

    expect(await screen.findByText("Password changed")).toBeInTheDocument();
    expect(sentBody).toEqual({
      current_password: CURRENT_PASSWORD,
      new_password: NEW_PASSWORD,
    });
    await waitFor(() =>
      expect(screen.getByLabelText(/^current password/i)).toHaveValue(""),
    );
    expect(screen.getByLabelText(/^new password/i)).toHaveValue("");
    expect(screen.getByLabelText(/^confirm new password/i)).toHaveValue("");
  });
});

describe("user menu", () => {
  it("links to the profile page", async () => {
    server.use(
      http.get("/api/clubs", () => HttpResponse.json(buildClubPage([]))),
    );
    const { user } = renderApp("/", { signedInAs: LEAD });

    await user.click(await screen.findByRole("button", { name: /lena lead/i }));
    await user.click(await screen.findByRole("menuitem", { name: /profile/i }));

    expect(await screen.findByText("Your details")).toBeInTheDocument();
  });
});
