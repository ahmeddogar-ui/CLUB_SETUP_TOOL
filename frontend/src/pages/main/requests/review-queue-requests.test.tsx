import {
  ADMIN,
  buildClubPage,
  buildRequestListItem,
  buildRequestPage,
  daysAgo,
  FINANCE,
  LEAD,
} from "@/test/builders";
import { renderApp } from "@/test/render-app";
import { server } from "@/test/server";
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

function serveAwaitingRequests() {
  const state: { query?: URLSearchParams } = {};
  server.use(
    http.get("/api/requests", ({ request }) => {
      state.query = new URL(request.url).searchParams;
      return HttpResponse.json(
        buildRequestPage([
          buildRequestListItem({
            title: "Tournament boards",
            status: "in_review",
            updated_at: daysAgo(3),
          }),
        ]),
      );
    }),
  );
  return state;
}

describe("review queue requests", () => {
  it("shows an admin both the clubs and the requests awaiting them", async () => {
    const state = serveAwaitingRequests();
    server.use(
      http.get("/api/clubs", () => HttpResponse.json(buildClubPage([]))),
    );
    renderApp("/review", { signedInAs: ADMIN });

    expect(await screen.findByText("Waiting for review")).toBeInTheDocument();
    expect(
      await screen.findByText("Requests awaiting you"),
    ).toBeInTheDocument();
    expect(
      await screen.findByRole("link", { name: "Tournament boards" }),
    ).toHaveAttribute("href", "/requests/100");
    expect(screen.getByText("Chess Club")).toBeInTheDocument();
    expect(screen.getByText("3 days")).toBeInTheDocument();
    expect(state.query?.get("awaiting_me")).toBe("true");
    expect(state.query?.get("sort")).toBe("oldest");
  });

  it("shows a finance approver only the requests card", async () => {
    serveAwaitingRequests();
    renderApp("/review", { signedInAs: FINANCE });

    expect(
      await screen.findByRole("link", { name: "Tournament boards" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Waiting for review")).not.toBeInTheDocument();
  });

  it("pages the requests with its own URL parameter", async () => {
    const offsets: (string | null)[] = [];
    server.use(
      http.get("/api/requests", ({ request }) => {
        offsets.push(new URL(request.url).searchParams.get("offset"));
        return HttpResponse.json(
          buildRequestPage([buildRequestListItem()], { total: 25 }),
        );
      }),
    );
    const { user } = renderApp("/review?requests_page=2", {
      signedInAs: FINANCE,
    });

    await screen.findByRole("link", { name: "Tournament boards" });
    await user.click(screen.getByRole("button", { name: "Previous" }));

    await screen.findByText("1–20 of 25");
    expect(offsets).toEqual(["20", "0"]);
  });

  it("sends a finance approver from the home page to the review queue", async () => {
    serveAwaitingRequests();
    renderApp("/", { signedInAs: FINANCE });

    expect(
      await screen.findByRole("link", { name: "Tournament boards" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Requests awaiting you")).toBeInTheDocument();
  });

  it("keeps a club lead out of the review queue", async () => {
    server.use(
      http.get("/api/clubs", () => HttpResponse.json(buildClubPage([]))),
    );
    renderApp("/review", { signedInAs: LEAD });

    expect(await screen.findByText("No clubs yet")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "My clubs" }),
    ).toBeInTheDocument();
  });

  it("shows a finance approver only the review queue in the sidebar", async () => {
    serveAwaitingRequests();
    const { user } = renderApp("/review", { signedInAs: FINANCE });
    await screen.findByRole("link", { name: "Tournament boards" });
    await user.click(screen.getByRole("button", { name: "Toggle sidebar" }));

    expect(
      await screen.findByRole("link", { name: "Review queue" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("link", { name: "Clubs" }),
    ).not.toBeInTheDocument();
  });
});
