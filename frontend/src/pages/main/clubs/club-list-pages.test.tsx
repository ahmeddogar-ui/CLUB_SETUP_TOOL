import {
  ADMIN,
  buildClub,
  buildClubListItem,
  buildClubPage,
  buildEvent,
  buildRequestPage,
  buildRequirements,
  daysAgo,
  LEAD,
} from "@/test/builders";
import { renderApp } from "@/test/render-app";
import { server } from "@/test/server";
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it, vi } from "vitest";

/** The review queue also asks for the requests awaiting the admin. */
function serveNoAwaitingRequests() {
  server.use(
    http.get("/api/requests", () => HttpResponse.json(buildRequestPage([]))),
  );
}

describe("club list", () => {
  it("lists the lead's clubs with status, document progress and last update", async () => {
    server.use(
      http.get("/api/clubs", () =>
        HttpResponse.json(
          buildClubPage([
            buildClubListItem({
              id: 1,
              name: "Chess Club",
              documents_provided: 3,
              updated_at: daysAgo(2),
            }),
            buildClubListItem({ id: 2, name: "Film Club", status: "approved" }),
          ]),
        ),
      ),
    );
    renderApp("/", { signedInAs: LEAD });

    expect(
      await screen.findByRole("link", { name: "Chess Club" }),
    ).toHaveAttribute("href", "/clubs/1");
    expect(screen.getByText("Approved")).toBeInTheDocument();
    expect(screen.getByText("3/4 documents")).toBeInTheDocument();
    expect(screen.getAllByText("2 days ago")).toHaveLength(2);
    expect(
      screen.queryByRole("columnheader", { name: "Owner" }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /new club/i })).toHaveAttribute(
      "href",
      "/clubs/new",
    );
  });

  it("invites a lead with no clubs to create one", async () => {
    server.use(
      http.get("/api/clubs", () => HttpResponse.json(buildClubPage([]))),
    );
    renderApp("/", { signedInAs: LEAD });

    expect(await screen.findByText("No clubs yet")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Create your first club" }),
    ).toHaveAttribute("href", "/clubs/new");
  });

  it("shows the backend's message when the list fails to load", async () => {
    server.use(
      http.get("/api/clubs", () =>
        HttpResponse.json({ detail: "Database unavailable" }, { status: 503 }),
      ),
    );
    renderApp("/", { signedInAs: LEAD });

    expect(await screen.findByText("Could not load clubs")).toBeInTheDocument();
    expect(screen.getByText("Database unavailable")).toBeInTheDocument();
  });

  it("pages through a long list", async () => {
    const offsets: (string | null)[] = [];
    server.use(
      http.get("/api/clubs", ({ request }) => {
        const offset = new URL(request.url).searchParams.get("offset");
        offsets.push(offset);
        const name = offset === "20" ? "Second page club" : "First page club";
        return HttpResponse.json(
          buildClubPage([buildClubListItem({ name })], { total: 25 }),
        );
      }),
    );
    const { user } = renderApp("/", { signedInAs: LEAD });

    expect(await screen.findByText("1–20 of 25")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Next" }));

    expect(
      await screen.findByRole("link", { name: "Second page club" }),
    ).toBeInTheDocument();
    expect(screen.getByText("21–25 of 25")).toBeInTheDocument();
    expect(offsets).toEqual(["0", "20"]);
  });
});

describe("list loading states", () => {
  it("shows skeleton rows while the next page loads", async () => {
    let releaseSecondPage = () => {};
    const secondPage = new Promise<void>((resolve) => {
      releaseSecondPage = resolve;
    });
    server.use(
      http.get("/api/clubs", async ({ request }) => {
        const offset = new URL(request.url).searchParams.get("offset");
        if (offset === "20") await secondPage;
        const name = offset === "20" ? "Second page club" : "First page club";
        return HttpResponse.json(
          buildClubPage([buildClubListItem({ name })], { total: 25 }),
        );
      }),
    );
    const { user } = renderApp("/", { signedInAs: LEAD });
    await screen.findByRole("link", { name: "First page club" });

    await user.click(screen.getByRole("button", { name: "Next" }));

    expect(
      await screen.findByRole("status", { name: "Loading clubs" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "First page club" }),
    ).not.toBeInTheDocument();
    releaseSecondPage();
    expect(
      await screen.findByRole("link", { name: "Second page club" }),
    ).toBeInTheDocument();
  });

  it("puts the page name in the browser tab", async () => {
    server.use(
      http.get("/api/clubs", () => HttpResponse.json(buildClubPage([]))),
    );
    serveNoAwaitingRequests();
    renderApp("/review", { signedInAs: ADMIN });

    await waitFor(() =>
      expect(document.title).toBe("Review queue · Club Setup"),
    );
  });
});

describe("all clubs (admin)", () => {
  it("sorts by a column on the server, flipping the order on a second click", async () => {
    const queries: URLSearchParams[] = [];
    server.use(
      http.get("/api/clubs", ({ request }) => {
        queries.push(new URL(request.url).searchParams);
        return HttpResponse.json(buildClubPage([buildClubListItem()]));
      }),
    );
    const { user } = renderApp("/", { signedInAs: ADMIN });
    await screen.findByRole("link", { name: "Chess Club" });
    expect(queries.at(-1)?.get("sort")).toBe("updated");
    expect(queries.at(-1)?.get("order")).toBe("desc");

    await user.click(screen.getByRole("button", { name: /^Club/ }));
    await waitFor(() => expect(queries.at(-1)?.get("sort")).toBe("name"));
    expect(queries.at(-1)?.get("order")).toBe("asc");
    expect(screen.getByRole("columnheader", { name: /^Club/ })).toHaveAttribute(
      "aria-sort",
      "ascending",
    );

    await user.click(screen.getByRole("button", { name: /^Club/ }));
    await waitFor(() => expect(queries.at(-1)?.get("order")).toBe("desc"));
    expect(screen.getByRole("columnheader", { name: /^Club/ })).toHaveAttribute(
      "aria-sort",
      "descending",
    );
  });

  it("sorts by last update newest first on the first click", async () => {
    const queries: URLSearchParams[] = [];
    server.use(
      http.get("/api/clubs", ({ request }) => {
        queries.push(new URL(request.url).searchParams);
        return HttpResponse.json(buildClubPage([buildClubListItem()]));
      }),
    );
    const { user } = renderApp("/?sort=name&order=asc&page=3", {
      signedInAs: ADMIN,
    });
    await screen.findByRole("link", { name: "Chess Club" });

    await user.click(screen.getByRole("button", { name: /^Last updated/ }));

    await waitFor(() => expect(queries.at(-1)?.get("sort")).toBe("updated"));
    expect(queries.at(-1)?.get("order")).toBe("desc");
    expect(queries.at(-1)?.get("offset")).toBe("0");
  });

  it("falls back to newest first for a sort it doesn't know", async () => {
    let query: URLSearchParams | undefined;
    server.use(
      http.get("/api/clubs", ({ request }) => {
        query = new URL(request.url).searchParams;
        return HttpResponse.json(buildClubPage([buildClubListItem()]));
      }),
    );
    renderApp("/?sort=documents&order=up", { signedInAs: ADMIN });
    await screen.findByRole("link", { name: "Chess Club" });

    expect(query?.get("sort")).toBe("updated");
    expect(query?.get("order")).toBe("desc");
  });

  function serveAllClubs(page = buildClubPage([])) {
    const queries: URLSearchParams[] = [];
    server.use(
      http.get("/api/clubs", ({ request }) => {
        queries.push(new URL(request.url).searchParams);
        return HttpResponse.json(page);
      }),
    );
    return queries;
  }

  it("shows each club's owner and no redundant card heading", async () => {
    serveAllClubs(
      buildClubPage([buildClubListItem({ owner_name: "Lena Lead" })]),
    );
    renderApp("/", { signedInAs: ADMIN });

    expect(
      await screen.findByRole("columnheader", { name: "Owner" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Lena Lead" })).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "All clubs" }),
    ).toBeInTheDocument();
    expect(
      document.querySelector("[data-slot=card-title]"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /new club/i }),
    ).not.toBeInTheDocument();
  });

  it("summarises how many clubs are in each status", async () => {
    serveAllClubs(
      buildClubPage([], {
        status_counts: {
          drafting: 0,
          submitted: 2,
          under_review: 1,
          changes_requested: 0,
          approved: 7,
          rejected: 1,
        },
      }),
    );
    renderApp("/", { signedInAs: ADMIN });

    const summary = await screen.findByRole("region", {
      name: "Clubs by status",
    });
    expect(within(summary).getByText("Approved").nextSibling).toHaveTextContent(
      "7",
    );
    // Drafts are their leads' own until submitted: no card, no tab.
    expect(within(summary).queryByText("Drafting")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Drafting" }),
    ).not.toBeInTheDocument();
  });

  it("filters by status on the server and starts again from the first page", async () => {
    const queries = serveAllClubs(
      buildClubPage([buildClubListItem()], { total: 45 }),
    );
    const { user } = renderApp("/", { signedInAs: ADMIN });

    await user.click(await screen.findByRole("button", { name: "Next" }));
    await user.click(screen.getByRole("button", { name: "Under review" }));

    const last = queries.at(-1);
    expect(last?.getAll("status")).toEqual(["under_review"]);
    expect(last?.get("offset")).toBe("0");
    expect(
      screen.getByRole("button", { name: "Under review" }),
    ).toHaveAttribute("aria-pressed", "true");
  });

  it("searches by name on the server", async () => {
    const queries = serveAllClubs();
    const { user } = renderApp("/", { signedInAs: ADMIN });

    await user.type(
      await screen.findByRole("searchbox", { name: "Search clubs by name" }),
      "chess",
    );
    await user.click(screen.getByRole("button", { name: "Search" }));

    await vi.waitFor(() => expect(queries.at(-1)?.get("q")).toBe("chess"));
  });

  it("offers to clear the filters when nothing matches", async () => {
    const queries = serveAllClubs();
    const { user } = renderApp("/?status=rejected&q=zzz", {
      signedInAs: ADMIN,
    });

    expect(await screen.findByText("No clubs match")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Clear filters" }));

    await vi.waitFor(() => {
      expect(queries.at(-1)?.get("q")).toBeNull();
      expect(queries.at(-1)?.getAll("status")).toEqual([]);
    });
  });
});

describe("export (admin)", () => {
  function serveExport() {
    Object.assign(URL, {
      createObjectURL: vi.fn(() => "blob:clubs"),
      revokeObjectURL: vi.fn(),
    });
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined);
    const queries: URLSearchParams[] = [];
    server.use(
      http.get("/api/clubs", () => HttpResponse.json(buildClubPage([]))),
      http.get("/api/clubs/export.csv", ({ request }) => {
        queries.push(new URL(request.url).searchParams);
        return new HttpResponse("id,name\n", {
          headers: { "Content-Type": "text/csv" },
        });
      }),
    );
    return { queries, click };
  }

  it("downloads the clubs matching the status and search on screen", async () => {
    const { queries, click } = serveExport();
    const { user } = renderApp(
      "/?status=submitted&q=chess&sort=name&order=desc",
      {
        signedInAs: ADMIN,
      },
    );

    await user.click(await screen.findByRole("button", { name: "Export CSV" }));

    await vi.waitFor(() => expect(queries).toHaveLength(1));
    expect(queries[0].getAll("status")).toEqual(["submitted"]);
    expect(queries[0].get("q")).toBe("chess");
    expect(queries[0].get("sort")).toBe("name");
    expect(queries[0].get("order")).toBe("desc");
    expect(queries[0].has("limit")).toBe(false);
    expect(queries[0].has("offset")).toBe(false);
    expect(click).toHaveBeenCalledOnce();
    expect(await screen.findByText("Export downloaded")).toBeInTheDocument();
  });

  it("shows the backend's message when the export fails", async () => {
    serveExport();
    server.use(
      http.get("/api/clubs/export.csv", () =>
        HttpResponse.json({ detail: "Database unavailable" }, { status: 503 }),
      ),
    );
    const { user } = renderApp("/", { signedInAs: ADMIN });

    await user.click(await screen.findByRole("button", { name: "Export CSV" }));

    expect(await screen.findByText("Database unavailable")).toBeInTheDocument();
    expect(screen.queryByText("Export downloaded")).not.toBeInTheDocument();
  });

  it("is not offered to a club lead", async () => {
    server.use(
      http.get("/api/clubs", () => HttpResponse.json(buildClubPage([]))),
    );
    renderApp("/", { signedInAs: LEAD });

    await screen.findByText("No clubs yet");
    expect(
      screen.queryByRole("button", { name: "Export CSV" }),
    ).not.toBeInTheDocument();
  });
});

describe("review queue", () => {
  it("asks for submitted and under-review clubs, oldest first, and shows how long each has waited", async () => {
    let query: URLSearchParams | undefined;
    server.use(
      http.get("/api/clubs", ({ request }) => {
        query = new URL(request.url).searchParams;
        return HttpResponse.json(
          buildClubPage([
            buildClubListItem({
              name: "Chess Club",
              status: "submitted",
              updated_at: daysAgo(3),
            }),
            buildClubListItem({
              id: 11,
              name: "Film Club",
              status: "under_review",
              updated_at: daysAgo(0),
            }),
          ]),
        );
      }),
    );
    serveNoAwaitingRequests();
    renderApp("/review", { signedInAs: ADMIN });

    expect(
      await screen.findByRole("link", { name: "Chess Club" }),
    ).toBeInTheDocument();
    expect(query?.getAll("status")).toEqual(["submitted", "under_review"]);
    expect(query?.get("sort")).toBe("updated");
    expect(query?.get("order")).toBe("asc");
    expect(screen.getByText("3 days")).toBeInTheDocument();
    expect(screen.getByText("Less than a day")).toBeInTheDocument();
  });

  it("offers the first page when a later page has emptied", async () => {
    const offsets: (string | null)[] = [];
    server.use(
      http.get("/api/clubs", ({ request }) => {
        const offset = new URL(request.url).searchParams.get("offset");
        offsets.push(offset);
        const items = offset === "0" ? [buildClubListItem()] : [];
        return HttpResponse.json(buildClubPage(items, { total: 5 }));
      }),
    );
    serveNoAwaitingRequests();
    const { user } = renderApp("/review?page=2", { signedInAs: ADMIN });

    expect(
      await screen.findByText("No clubs on this page"),
    ).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "Go to the first page" }),
    );

    expect(
      await screen.findByRole("link", { name: "Chess Club" }),
    ).toBeInTheDocument();
    expect(offsets).toEqual(["20", "0"]);
  });

  it("points to all clubs when nothing is waiting", async () => {
    server.use(
      http.get("/api/clubs", () => HttpResponse.json(buildClubPage([]))),
    );
    serveNoAwaitingRequests();
    renderApp("/review", { signedInAs: ADMIN });

    expect(
      await screen.findByText("Nothing waiting for review"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "View all clubs" }),
    ).toHaveAttribute("href", "/");
  });
});

describe("new club", () => {
  it("creates the club and opens its page", async () => {
    let created: unknown;
    const club = buildClub({
      id: 42,
      name: "Go Club",
      description: "We play go",
    });
    server.use(
      http.post("/api/clubs", async ({ request }) => {
        created = await request.json();
        return HttpResponse.json(club, { status: 201 });
      }),
      http.get("/api/clubs/42", () => HttpResponse.json(club)),
      http.get("/api/clubs/42/requirements", () =>
        HttpResponse.json(buildRequirements(42)),
      ),
      http.get("/api/clubs/42/events", () => HttpResponse.json([buildEvent()])),
      http.get("/api/clubs/42/comments", () =>
        HttpResponse.json({ items: [], total: 0 }),
      ),
    );
    const { user } = renderApp("/clubs/new", { signedInAs: LEAD });

    await user.type(await screen.findByLabelText(/club name/i), "  Go Club ");
    await user.type(screen.getByLabelText(/description/i), "We play go");
    await user.click(screen.getByRole("button", { name: "Create club" }));

    expect(
      await screen.findByRole("heading", { name: "Go Club" }),
    ).toBeInTheDocument();
    expect(created).toEqual({ name: "Go Club", description: "We play go" });
  });

  it("requires a name and description before calling the backend", async () => {
    const { user } = renderApp("/clubs/new", { signedInAs: LEAD });

    await user.click(
      await screen.findByRole("button", { name: "Create club" }),
    );

    expect(
      await screen.findByText("Club name is required"),
    ).toBeInTheDocument();
    expect(screen.getByText("Description is required")).toBeInTheDocument();
  });

  it("refuses a name or description longer than the backend allows", async () => {
    const { user } = renderApp("/clubs/new", { signedInAs: LEAD });

    await user.click(await screen.findByLabelText(/^club name/i));
    await user.paste("a".repeat(101));
    await user.click(screen.getByLabelText(/^description/i));
    await user.paste("a".repeat(2001));
    await user.click(screen.getByRole("button", { name: "Create club" }));

    expect(
      await screen.findByText("Club name must be at most 100 characters"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Description must be at most 2000 characters"),
    ).toBeInTheDocument();
  });
});
