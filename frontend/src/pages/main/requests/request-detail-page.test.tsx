import type { RequestAction, RequestDetail } from "@/lib/request-types";
import type { User } from "@/lib/types";
import {
  ADMIN,
  buildRequestDetail,
  buildRequestEvent,
  FINANCE,
  LEAD,
  ROOM,
} from "@/test/builders";
import { renderApp } from "@/test/render-app";
import { server } from "@/test/server";
import { screen, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

const REQUEST_URL = "/requests/100";

const STRANGER: User = { ...LEAD, id: 99, name: "Sam Stranger" };

/** Serves one request's read endpoints; `state.request` can be changed by write handlers. */
function serveRequest(request: RequestDetail) {
  const state = { request };
  server.use(
    http.get(`/api${REQUEST_URL}`, () => HttpResponse.json(state.request)),
    http.get(`/api${REQUEST_URL}/events`, () =>
      HttpResponse.json([
        buildRequestEvent({
          id: 2,
          event_type: "request_submitted",
          note: "Please hurry",
        }),
        buildRequestEvent(),
      ]),
    ),
  );
  return state;
}

async function openRequest(request: RequestDetail, signedInAs: User = LEAD) {
  const state = serveRequest(request);
  const rendered = renderApp(REQUEST_URL, { signedInAs });
  await screen.findByRole("heading", { name: request.title });
  return { ...rendered, state };
}

function withActions(
  allowed_actions: RequestAction[],
  overrides: Partial<RequestDetail> = {},
) {
  return buildRequestDetail({ allowed_actions, ...overrides });
}

describe("request details", () => {
  it("shows the status, club, type and the funding line items with a total", async () => {
    await openRequest(buildRequestDetail({ status: "in_review", round: 2 }));

    expect(screen.getByText("In review")).toBeInTheDocument();
    expect(screen.getByText("Round 2")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Chess Club" })).toHaveAttribute(
      "href",
      "/clubs/10",
    );
    const boards = screen.getByRole("row", { name: /Chess boards/ });
    expect(within(boards).getByText("$125.50")).toBeInTheDocument();
    const total = screen.getByRole("row", { name: /Total/ });
    expect(within(total).getByText("$175.50")).toBeInTheDocument();
  });

  it("shows the room and the time range of a booking", async () => {
    await openRequest(
      buildRequestDetail({
        request_type: "room_booking",
        title: "Club night",
        approval_steps: ["admin"],
        details: {
          request_type: "room_booking",
          room_id: ROOM.id,
          room_name: ROOM.name,
          starts_at: "2030-01-15T19:00:00Z",
          ends_at: "2030-01-15T21:00:00Z",
        },
      }),
    );

    expect(screen.getByText(ROOM.name)).toBeInTheDocument();
    expect(screen.queryByText("Round 2")).not.toBeInTheDocument();
  });

  it("lists the approval steps with who approved, who is awaited and what hasn't started", async () => {
    await openRequest(
      buildRequestDetail({
        status: "in_review",
        awaiting_role: "finance_approver",
        approvals: [
          {
            step: 0,
            role: "admin",
            approver_name: "Ada Admin",
            approved_at: "2026-11-02T12:00:00Z",
            note: "Looks good",
          },
        ],
      }),
    );

    const steps = within(
      screen.getByRole("list", { name: "Approval steps" }),
    ).getAllByRole("listitem");
    expect(steps).toHaveLength(2);
    expect(steps[0]).toHaveTextContent("Admin");
    expect(steps[0]).toHaveTextContent("Ada Admin");
    expect(steps[0]).toHaveTextContent("Looks good");
    expect(steps[1]).toHaveTextContent("Finance approver");
    expect(steps[1]).toHaveTextContent("Waiting");
  });

  it("says a step has not started before the request is reviewed", async () => {
    await openRequest(buildRequestDetail());

    const steps = within(
      screen.getByRole("list", { name: "Approval steps" }),
    ).getAllByRole("listitem");
    expect(steps[0]).toHaveTextContent("Not started");
    expect(steps[1]).toHaveTextContent("Not started");
  });

  it("lists the request's history", async () => {
    await openRequest(buildRequestDetail());

    const history = screen.getByRole("row", { name: /Submitted for review/ });
    expect(within(history).getByText("Please hurry")).toBeInTheDocument();
    expect(screen.getByText("Request created")).toBeInTheDocument();
  });

  it("shows a finance approver the club's name without a link they can't open", async () => {
    await openRequest(withActions(["approve"]), FINANCE);

    expect(
      screen.queryByRole("link", { name: "Chess Club" }),
    ).not.toBeInTheDocument();
    expect(screen.getByText(/request for Chess Club/)).toBeInTheDocument();
  });
});

describe("request actions", () => {
  it("shows exactly the actions the backend allows", async () => {
    await openRequest(
      withActions(["approve", "reject", "request_changes"], {
        status: "in_review",
      }),
      ADMIN,
    );

    for (const name of ["Approve", "Request changes", "Reject"]) {
      expect(screen.getByRole("button", { name })).toBeInTheDocument();
    }
    for (const name of [
      "Submit for review",
      "Start review",
      "Cancel request",
      "Edit",
    ]) {
      expect(screen.queryByRole("button", { name })).not.toBeInTheDocument();
    }
  });

  it("shows no actions to someone with none allowed", async () => {
    await openRequest(withActions([]), STRANGER);

    for (const name of [
      "Submit for review",
      "Approve",
      "Cancel request",
      "Edit",
    ]) {
      expect(screen.queryByRole("button", { name })).not.toBeInTheDocument();
    }
  });

  it("submits the draft and shows the new status", async () => {
    const { user, state } = await openRequest(
      withActions(["submit", "cancel"]),
    );
    server.use(
      http.post(`/api${REQUEST_URL}/submit`, () => {
        state.request = withActions(["cancel"], { status: "submitted" });
        return HttpResponse.json(state.request);
      }),
    );

    await user.click(screen.getByRole("button", { name: "Submit for review" }));

    expect(
      await screen.findByText("Request submitted for review"),
    ).toBeInTheDocument();
    expect(await screen.findByText("Submitted")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Submit for review" }),
    ).not.toBeInTheDocument();
  });

  it("shows the backend's double-booking message inline when submit is refused", async () => {
    const message =
      "DV 2074 is already booked for part of that time. Choose another time or room.";
    const { user } = await openRequest(withActions(["submit"]));
    server.use(
      http.post(`/api${REQUEST_URL}/submit`, () =>
        HttpResponse.json({ detail: message }, { status: 409 }),
      ),
    );

    await user.click(screen.getByRole("button", { name: "Submit for review" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(message);
  });

  it("offers Resubmit after changes were requested", async () => {
    await openRequest(withActions(["submit"], { status: "changes_requested" }));

    expect(
      screen.getByRole("button", { name: "Resubmit" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Submit for review" }),
    ).not.toBeInTheDocument();
  });

  it("starts the review", async () => {
    const { user } = await openRequest(
      withActions(["start_review"], { status: "submitted" }),
      ADMIN,
    );
    let started = false;
    server.use(
      http.post(`/api${REQUEST_URL}/start-review`, () => {
        started = true;
        return HttpResponse.json(withActions([], { status: "in_review" }));
      }),
    );

    await user.click(screen.getByRole("button", { name: "Start review" }));

    expect(await screen.findByText("Review started")).toBeInTheDocument();
    expect(started).toBe(true);
  });

  it("approves with an optional note", async () => {
    const { user } = await openRequest(withActions(["approve"]), ADMIN);
    let sent: unknown;
    server.use(
      http.post(`/api${REQUEST_URL}/approve`, async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json(withActions([], { status: "in_review" }));
      }),
    );

    await user.click(screen.getByRole("button", { name: "Approve" }));
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByRole("textbox"), "Within budget");
    await user.click(within(dialog).getByRole("button", { name: "Approve" }));

    expect(await screen.findByText("Approval recorded")).toBeInTheDocument();
    expect(sent).toEqual({ note: "Within budget" });
  });

  it("asks for confirmation, showing the note, before rejecting", async () => {
    const { user } = await openRequest(withActions(["reject"]), ADMIN);
    let sent: unknown;
    server.use(
      http.post(`/api${REQUEST_URL}/reject`, async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json(withActions([], { status: "rejected" }));
      }),
    );

    await user.click(screen.getByRole("button", { name: "Reject" }));
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByRole("textbox"), "Over budget");
    await user.click(within(dialog).getByRole("button", { name: "Reject" }));

    expect(
      within(dialog).getByText("Reject Tournament boards?"),
    ).toBeInTheDocument();
    expect(sent).toBeUndefined();

    await user.click(
      within(dialog).getByRole("button", { name: "Yes, reject" }),
    );

    expect(await screen.findByText("Request rejected")).toBeInTheDocument();
    expect(sent).toEqual({ note: "Over budget" });
  });

  it("requests changes with a required note", async () => {
    const { user } = await openRequest(withActions(["request_changes"]), ADMIN);
    let sent: unknown;
    server.use(
      http.post(`/api${REQUEST_URL}/request-changes`, async ({ request }) => {
        sent = await request.json();
        return HttpResponse.json(
          withActions([], { status: "changes_requested" }),
        );
      }),
    );

    await user.click(screen.getByRole("button", { name: "Request changes" }));
    const dialog = await screen.findByRole("dialog");
    expect(
      within(dialog).getByRole("button", { name: "Request changes" }),
    ).toBeDisabled();
    await user.type(within(dialog).getByRole("textbox"), "Add quotes");
    await user.click(
      within(dialog).getByRole("button", { name: "Request changes" }),
    );
    await user.click(
      within(dialog).getByRole("button", { name: "Yes, request changes" }),
    );

    expect(await screen.findByText("Changes requested")).toBeInTheDocument();
    expect(sent).toEqual({ note: "Add quotes" });
  });

  it("confirms before cancelling the request", async () => {
    const { user } = await openRequest(withActions(["cancel"]));
    let cancelled = false;
    server.use(
      http.post(`/api${REQUEST_URL}/cancel`, () => {
        cancelled = true;
        return HttpResponse.json(withActions([], { status: "cancelled" }));
      }),
    );

    await user.click(screen.getByRole("button", { name: "Cancel request" }));
    const dialog = await screen.findByRole("dialog");
    expect(cancelled).toBe(false);
    await user.click(
      within(dialog).getByRole("button", { name: "Yes, cancel request" }),
    );

    expect(await screen.findByText("Request cancelled")).toBeInTheDocument();
    expect(cancelled).toBe(true);
  });
});

describe("editing a request", () => {
  it("links the lead to the edit page while the request is a draft or has changes requested", async () => {
    await openRequest(buildRequestDetail());

    expect(screen.getByRole("button", { name: "Edit" })).toHaveAttribute(
      "href",
      "/requests/100/edit",
    );
  });

  it("hides Edit from everyone else and once the request is under review", async () => {
    await openRequest(buildRequestDetail({ status: "in_review" }));

    expect(
      screen.queryByRole("button", { name: "Edit" }),
    ).not.toBeInTheDocument();
  });

  it("hides Edit from an admin", async () => {
    await openRequest(buildRequestDetail(), ADMIN);

    expect(
      screen.queryByRole("button", { name: "Edit" }),
    ).not.toBeInTheDocument();
  });

  it("prefills the form, locks the type and saves the changes", async () => {
    const request = buildRequestDetail({ status: "changes_requested" });
    serveRequest(request);
    let sent: unknown;
    server.use(
      http.patch(`/api${REQUEST_URL}`, async ({ request: patch }) => {
        sent = await patch.json();
        return HttpResponse.json(request);
      }),
    );
    const { user } = renderApp(`${REQUEST_URL}/edit`, { signedInAs: LEAD });

    const title = await screen.findByLabelText(/^Title/);
    expect(title).toHaveValue("Tournament boards");
    expect(screen.getAllByLabelText(/^Amount/)[0]).toHaveValue("125.50");
    expect(screen.getByRole("radio", { name: /Room booking/ })).toBeDisabled();

    await user.clear(title);
    await user.type(title, "Tournament equipment");
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    expect(await screen.findByText("Request updated")).toBeInTheDocument();
    expect(sent).toEqual({
      title: "Tournament equipment",
      details: {
        request_type: "funding",
        line_items: [
          { description: "Chess boards", amount_cents: 12550 },
          { description: "Clocks", amount_cents: 5000 },
        ],
      },
    });
    expect(
      await screen.findByRole("heading", { name: "Tournament boards" }),
    ).toBeInTheDocument();
  });

  it("shows the backend's refusal inline when the save is refused", async () => {
    serveRequest(buildRequestDetail());
    server.use(
      http.patch(`/api${REQUEST_URL}`, () =>
        HttpResponse.json(
          { detail: "DV 2074 is already booked for part of that time." },
          { status: 409 },
        ),
      ),
    );
    const { user } = renderApp(`${REQUEST_URL}/edit`, { signedInAs: LEAD });

    await screen.findByLabelText(/^Title/);
    await user.click(screen.getByRole("button", { name: "Save changes" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "DV 2074 is already booked",
    );
  });
});
