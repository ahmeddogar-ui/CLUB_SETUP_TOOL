import { ADMIN, LEAD, buildClubPage, buildUserListItem } from "@/test/builders";
import { renderApp } from "@/test/render-app";
import { server } from "@/test/server";
import { screen, waitFor } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

function serveUsers(items = [buildUserListItem()]) {
  const queries: URLSearchParams[] = [];
  server.use(
    http.get("/api/users", ({ request }) => {
      queries.push(new URL(request.url).searchParams);
      return HttpResponse.json({ items, total: items.length });
    }),
  );
  return queries;
}

describe("users page", () => {
  it("lists users with their email and role", async () => {
    serveUsers([
      buildUserListItem(),
      buildUserListItem({
        id: 5,
        name: "Sam Second",
        email: "sam@example.com",
      }),
    ]);
    renderApp("/users", { signedInAs: ADMIN });

    expect(await screen.findByText("Lena Lead")).toBeInTheDocument();
    expect(screen.getByText("lena@example.com")).toBeInTheDocument();
    expect(screen.getByLabelText("Role for Sam Second")).toHaveValue(
      "club_lead",
    );
  });

  it("searches on the server", async () => {
    const queries = serveUsers();
    const { user } = renderApp("/users", { signedInAs: ADMIN });

    await user.type(
      await screen.findByRole("searchbox", { name: "Search users" }),
      "lena",
    );
    await user.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => expect(queries.at(-1)?.get("q")).toBe("lena"));
    expect(queries.at(-1)?.get("limit")).toBe("20");
  });

  it("filters by role and starts again from the first page", async () => {
    const queries = serveUsers();
    const { user } = renderApp("/users?page=2", { signedInAs: ADMIN });

    await user.click(
      await screen.findByRole("button", { name: "Administrator" }),
    );

    await waitFor(() => expect(queries.at(-1)?.get("role")).toBe("admin"));
    expect(queries.at(-1)?.get("offset")).toBe("0");
  });

  it("changes a role and confirms with a toast", async () => {
    serveUsers();
    let sentBody: unknown;
    server.use(
      http.patch("/api/users/1/role", async ({ request }) => {
        sentBody = await request.json();
        return HttpResponse.json({ ...LEAD, role: "admin" });
      }),
    );
    const { user } = renderApp("/users", { signedInAs: ADMIN });

    await user.selectOptions(
      await screen.findByLabelText("Role for Lena Lead"),
      "admin",
    );

    expect(
      await screen.findByText("Lena Lead is now Administrator"),
    ).toBeInTheDocument();
    expect(sentBody).toEqual({ role: "admin" });
  });

  it("shows the backend's reason when a role change is refused", async () => {
    serveUsers();
    server.use(
      http.patch("/api/users/1/role", () =>
        HttpResponse.json(
          { detail: "Lena Lead owns clubs and cannot be demoted" },
          { status: 409 },
        ),
      ),
    );
    const { user } = renderApp("/users", { signedInAs: ADMIN });

    await user.selectOptions(
      await screen.findByLabelText("Role for Lena Lead"),
      "admin",
    );

    expect(
      await screen.findByText("Lena Lead owns clubs and cannot be demoted"),
    ).toBeInTheDocument();
  });

  it("shows the signed-in admin's own role as text", async () => {
    serveUsers([buildUserListItem({ ...ADMIN })]);
    renderApp("/users", { signedInAs: ADMIN });

    expect(await screen.findByText("Administrator (you)")).toBeInTheDocument();
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });

  it("offers to clear the filters when nothing matches", async () => {
    const queries = serveUsers([]);
    const { user } = renderApp("/users?q=zzz&role=admin", {
      signedInAs: ADMIN,
    });

    expect(await screen.findByText("No users match")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Clear filters" }));

    await waitFor(() => {
      expect(queries.at(-1)?.get("q")).toBeNull();
      expect(queries.at(-1)?.get("role")).toBeNull();
    });
  });

  it("redirects a club lead to the clubs page", async () => {
    server.use(
      http.get("/api/clubs", () => HttpResponse.json(buildClubPage([]))),
    );
    renderApp("/users", { signedInAs: LEAD });

    expect(await screen.findByText("No clubs yet")).toBeInTheDocument();
  });
});
