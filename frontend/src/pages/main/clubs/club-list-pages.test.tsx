import {
  ADMIN,
  buildClub,
  buildEvent,
  buildRequirements,
  LEAD,
} from "@/test/builders";
import { renderApp } from "@/test/render-app";
import { server } from "@/test/server";
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

describe("club list", () => {
  it("lists the lead's clubs with their status and offers to create one", async () => {
    server.use(
      http.get("/api/clubs", () =>
        HttpResponse.json([
          buildClub({ id: 1, name: "Chess Club" }),
          buildClub({ id: 2, name: "Film Club", status: "approved" }),
        ]),
      ),
    );
    renderApp("/", { signedInAs: LEAD });

    expect(
      await screen.findByRole("link", { name: "Chess Club" }),
    ).toHaveAttribute("href", "/clubs/1");
    expect(screen.getByRole("link", { name: "Film Club" })).toHaveAttribute(
      "href",
      "/clubs/2",
    );
    expect(screen.getByText("Approved")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /new club/i })).toHaveAttribute(
      "href",
      "/clubs/new",
    );
  });

  it("does not offer club creation to an admin", async () => {
    server.use(http.get("/api/clubs", () => HttpResponse.json([])));
    renderApp("/", { signedInAs: ADMIN });

    expect(
      await screen.findByRole("heading", { name: "All clubs" }),
    ).toBeInTheDocument();
    expect(await screen.findByText("No clubs yet")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /new club/i }),
    ).not.toBeInTheDocument();
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
});

describe("review queue", () => {
  it("asks the backend for submitted and under-review clubs, oldest first", async () => {
    let query: URLSearchParams | undefined;
    server.use(
      http.get("/api/clubs", ({ request }) => {
        query = new URL(request.url).searchParams;
        return HttpResponse.json([buildClub({ status: "submitted" })]);
      }),
    );
    renderApp("/review", { signedInAs: ADMIN });

    expect(
      await screen.findByRole("link", { name: "Chess Club" }),
    ).toBeInTheDocument();
    expect(query?.getAll("status")).toEqual(["submitted", "under_review"]);
    expect(query?.get("sort")).toBe("oldest");
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
});
