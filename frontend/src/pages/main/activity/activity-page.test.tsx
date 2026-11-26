import { ADMIN, LEAD, buildActivityEntry } from "@/test/builders";
import { renderApp } from "@/test/render-app";
import { server } from "@/test/server";
import type { ActivityEntry } from "@/lib/types";
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

function serveActivity(
  items: ActivityEntry[] = [buildActivityEntry()],
  total = items.length,
) {
  const queries: URLSearchParams[] = [];
  server.use(
    http.get("/api/activity", ({ request }) => {
      queries.push(new URL(request.url).searchParams);
      return HttpResponse.json({ items, total });
    }),
  );
  return queries;
}

describe("activity page", () => {
  it("lists entries with readable actions, clubs and notes", async () => {
    serveActivity([
      buildActivityEntry({
        id: 1,
        event_type: "requirement_approved",
        requirement_type: "budget",
        actor_id: ADMIN.id,
        actor_name: ADMIN.name,
        note: "Looks good",
      }),
      buildActivityEntry({
        id: 2,
        event_type: "role_changed",
        actor_id: ADMIN.id,
        actor_name: ADMIN.name,
        club_id: null,
        club_name: null,
        subject_user_id: LEAD.id,
        subject_user_name: "Lena Lead",
      }),
      buildActivityEntry({ id: 3, event_type: "created" }),
    ]);
    renderApp("/activity", { signedInAs: ADMIN });

    expect(
      await screen.findByText("Requirement approved · Budget"),
    ).toBeInTheDocument();
    expect(screen.getByText("Looks good")).toBeInTheDocument();
    expect(
      screen.getByRole("cell", { name: "Club created" }),
    ).toBeInTheDocument();
    const roleRow = screen.getByRole("row", { name: /Role changed/ });
    expect(within(roleRow).getByText("Lena Lead")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Chess Club" })).toHaveLength(
      2,
    );
  });

  it("filters by actor from a name, shows a chip, and removes it again", async () => {
    const queries = serveActivity();
    const { user } = renderApp("/activity", { signedInAs: ADMIN });

    await user.click(
      await screen.findByRole("button", { name: "Show activity by Lena Lead" }),
    );

    await waitFor(() =>
      expect(queries.at(-1)?.get("actor_id")).toBe(String(LEAD.id)),
    );
    expect(await screen.findByText("By: Lena Lead")).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: "Remove filter By: Lena Lead" }),
    );

    await waitFor(() => expect(queries.at(-1)?.get("actor_id")).toBeNull());
    expect(screen.queryByText("By: Lena Lead")).not.toBeInTheDocument();
  });

  it("filters by club from a club name", async () => {
    const queries = serveActivity();
    const { user } = renderApp("/activity", { signedInAs: ADMIN });

    await user.click(await screen.findByRole("button", { name: "Chess Club" }));

    await waitFor(() => expect(queries.at(-1)?.get("club_id")).toBe("10"));
    expect(await screen.findByText("Club: Chess Club")).toBeInTheDocument();
  });

  it("falls back to the id for a filter no row explains", async () => {
    serveActivity();
    renderApp("/activity?actor_id=99", { signedInAs: ADMIN });

    expect(await screen.findByText("By: #99")).toBeInTheDocument();
  });

  it("filters by event type", async () => {
    const queries = serveActivity();
    const { user } = renderApp("/activity", { signedInAs: ADMIN });

    await user.selectOptions(
      await screen.findByLabelText("Action"),
      "Comment posted",
    );

    await waitFor(() =>
      expect(queries.at(-1)?.get("event_type")).toBe("comment_posted"),
    );
  });

  it("sends the date range as the start of the first day and the day after the last", async () => {
    const queries = serveActivity();
    const { user } = renderApp("/activity", { signedInAs: ADMIN });

    await user.type(await screen.findByLabelText("From"), "2026-11-01");
    await user.type(screen.getByLabelText("To"), "2026-11-30");

    await waitFor(() =>
      expect(queries.at(-1)?.get("until")).toBe(
        new Date(2026, 11, 1).toISOString(),
      ),
    );
    expect(queries.at(-1)?.get("since")).toBe(
      new Date(2026, 10, 1).toISOString(),
    );
  });

  it("clears every filter at once", async () => {
    const queries = serveActivity();
    const { user } = renderApp("/activity?actor_id=1&event_type=approved", {
      signedInAs: ADMIN,
    });

    await user.click(
      await screen.findByRole("button", { name: "Clear filters" }),
    );

    await waitFor(() => {
      expect(queries.at(-1)?.get("actor_id")).toBeNull();
      expect(queries.at(-1)?.get("event_type")).toBeNull();
    });
  });

  it("says when nothing matches", async () => {
    serveActivity([]);
    renderApp("/activity?event_type=approved", { signedInAs: ADMIN });

    expect(await screen.findByText("No activity matches")).toBeInTheDocument();
  });

  it("pages through a long log", async () => {
    const queries = serveActivity([buildActivityEntry()], 25);
    const { user } = renderApp("/activity", { signedInAs: ADMIN });

    expect(await screen.findByText("1–20 of 25")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Next" }));

    await waitFor(() => expect(queries.at(-1)?.get("offset")).toBe("20"));
    expect(queries.at(-1)?.get("limit")).toBe("20");
  });
});
