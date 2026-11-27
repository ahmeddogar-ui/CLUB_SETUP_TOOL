import type { Club } from "@/lib/types";
import {
  ADMIN,
  buildClub,
  buildEvent,
  buildRequestListItem,
  buildRequestPage,
  LEAD,
} from "@/test/builders";
import { renderApp } from "@/test/render-app";
import { server } from "@/test/server";
import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

const CLUB_URL = "/clubs/10";

function serveClub(club: Club) {
  server.use(
    http.get(`/api${CLUB_URL}`, () => HttpResponse.json(club)),
    http.get(`/api${CLUB_URL}/requirements`, () => HttpResponse.json([])),
    http.get(`/api${CLUB_URL}/events`, () => HttpResponse.json([buildEvent()])),
    http.get(`/api${CLUB_URL}/comments`, () =>
      HttpResponse.json({ items: [], total: 0 }),
    ),
  );
}

function serveRequests(items = buildRequestPage([])) {
  const state: { query?: URLSearchParams } = {};
  server.use(
    http.get("/api/requests", ({ request }) => {
      state.query = new URL(request.url).searchParams;
      return HttpResponse.json(items);
    }),
  );
  return state;
}

describe("club requests tab", () => {
  it("lists the club's requests, newest first, and keeps the tab in the URL", async () => {
    const club = buildClub({ status: "approved" });
    serveClub(club);
    const state = serveRequests(
      buildRequestPage([
        buildRequestListItem({ title: "Tournament boards" }),
        buildRequestListItem({
          id: 101,
          title: "Club night",
          request_type: "room_booking",
          status: "approved",
          total_cents: null,
          room_name: "DV 2074",
          starts_at: "2026-12-01T18:00:00Z",
          ends_at: "2026-12-01T20:00:00Z",
        }),
      ]),
    );
    const { user } = renderApp(CLUB_URL, { signedInAs: LEAD });
    await screen.findByRole("heading", { name: club.name });

    await user.click(screen.getByRole("tab", { name: "Requests" }));

    const link = await screen.findByRole("link", { name: "Tournament boards" });
    expect(link).toHaveAttribute("href", "/requests/100");
    expect(
      screen.getByRole("link", { name: "Club night" }),
    ).toBeInTheDocument();
    expect(screen.getByText("$175.50")).toBeInTheDocument();
    expect(screen.getByText(/DV 2074/)).toBeInTheDocument();
    expect(screen.getByText("Approved")).toBeInTheDocument();
    expect(state.query?.get("club_id")).toBe("10");
    expect(state.query?.get("sort")).toBe("newest");
    expect(state.query?.get("limit")).toBe("20");
    expect(screen.getByRole("tab", { name: "Requests" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("opens on the tab named in the URL and says when there are no requests", async () => {
    serveClub(buildClub({ status: "approved" }));
    serveRequests();
    renderApp(`${CLUB_URL}?tab=requests`, { signedInAs: LEAD });

    expect(await screen.findByText("No requests yet.")).toBeInTheDocument();
  });

  it("offers New request to the lead of an approved club", async () => {
    serveClub(buildClub({ status: "approved" }));
    serveRequests();
    renderApp(`${CLUB_URL}?tab=requests`, { signedInAs: LEAD });

    expect(
      await screen.findByRole("button", { name: "New request" }),
    ).toHaveAttribute("href", "/clubs/10/requests/new");
  });

  it("says requests open once a drafting club is approved", async () => {
    serveClub(buildClub({ status: "drafting" }));
    serveRequests();
    renderApp(`${CLUB_URL}?tab=requests`, { signedInAs: LEAD });

    expect(
      await screen.findByText("Requests open once the club is approved."),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "New request" }),
    ).not.toBeInTheDocument();
  });

  it("hides New request from an admin", async () => {
    serveClub(buildClub({ status: "approved" }));
    serveRequests();
    renderApp(`${CLUB_URL}?tab=requests`, { signedInAs: ADMIN });

    expect(await screen.findByText("No requests yet.")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "New request" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("Requests open once the club is approved."),
    ).not.toBeInTheDocument();
  });

  it("shows the overview by default", async () => {
    serveClub(buildClub());
    renderApp(CLUB_URL, { signedInAs: LEAD });

    const tablist = await screen.findByRole("tablist");
    expect(
      within(tablist).getByRole("tab", { name: "Overview" }),
    ).toHaveAttribute("aria-selected", "true");
    expect(await screen.findByText("We play chess")).toBeInTheDocument();
  });
});
