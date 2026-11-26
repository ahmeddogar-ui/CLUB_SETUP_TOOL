import type { Club, Requirement } from "@/lib/types";
import {
  ADMIN,
  buildClub,
  buildEvent,
  buildRequirements,
  LEAD,
} from "@/test/builders";
import { renderApp } from "@/test/render-app";
import { server } from "@/test/server";
import { screen, waitFor, within } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

const CLUB_ID = 10;
const CLUB_URL = `/clubs/${CLUB_ID}`;

/** Serves one club's three read endpoints; `state` can be mutated by write handlers. */
function serveClub(
  club: Club,
  requirements: Requirement[] = buildRequirements(club.id),
) {
  const state = { club, requirements };
  server.use(
    http.get(`/api${CLUB_URL}`, () => HttpResponse.json(state.club)),
    http.get(`/api${CLUB_URL}/requirements`, () =>
      HttpResponse.json(state.requirements),
    ),
    http.get(`/api${CLUB_URL}/events`, () => HttpResponse.json([buildEvent()])),
  );
  return state;
}

async function openClub(club: Club, signedInAs = LEAD) {
  const rendered = renderApp(CLUB_URL, { signedInAs });
  await screen.findByRole("heading", { name: club.name });
  return rendered;
}

function requirementRow(label: string) {
  return screen.getByRole("row", { name: new RegExp(label) });
}

describe("club detail as the owning club lead", () => {
  it("marks Clubs as the current section in the sidebar", async () => {
    const club = buildClub();
    serveClub(club);
    const { user } = await openClub(club);
    // jsdom's window is narrower than the sidebar's breakpoint: it's a drawer.
    await user.click(screen.getByRole("button", { name: "Toggle sidebar" }));

    expect(await screen.findByRole("link", { name: "Clubs" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("offers edit, submit and document links while drafting, and no review controls", async () => {
    const club = buildClub();
    serveClub(club);
    await openClub(club);

    expect(screen.getByRole("button", { name: /edit/i })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Submit for review" }),
    ).toBeInTheDocument();
    expect(
      screen.getAllByRole("button", { name: "Provide link" }),
    ).toHaveLength(4);
    expect(
      screen.queryByRole("button", { name: "Start review" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Approve club" }),
    ).not.toBeInTheDocument();
  });

  it("submits and shows the new status the backend returns", async () => {
    const club = buildClub();
    const state = serveClub(club);
    server.use(
      http.post(`/api${CLUB_URL}/submit`, () => {
        state.club = { ...state.club, status: "submitted" };
        return HttpResponse.json(state.club);
      }),
    );
    const { user } = await openClub(club);

    await user.click(screen.getByRole("button", { name: "Submit for review" }));

    expect(
      await screen.findByText("Club submitted for review"),
    ).toBeInTheDocument();
    expect(await screen.findByText("Submitted")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Submit for review" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /edit/i }),
    ).not.toBeInTheDocument();
  });

  it("shows the backend's reason when submit is blocked", async () => {
    const club = buildClub();
    serveClub(club);
    server.use(
      http.post(`/api${CLUB_URL}/submit`, () =>
        HttpResponse.json(
          { detail: "missing: constitution, budget" },
          { status: 409 },
        ),
      ),
    );
    const { user } = await openClub(club);

    await user.click(screen.getByRole("button", { name: "Submit for review" }));

    // Inline, not a toast: the lead needs it while fixing the documents.
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "missing: constitution, budget",
    );
  });

  it("resubmits through the resubmit endpoint after changes were requested", async () => {
    const club = buildClub({ status: "changes_requested" });
    const state = serveClub(club);
    server.use(
      http.post(`/api${CLUB_URL}/resubmit`, () => {
        state.club = { ...state.club, status: "submitted" };
        return HttpResponse.json(state.club);
      }),
    );
    const { user } = await openClub(club);

    await user.click(
      screen.getByRole("button", { name: "Resubmit for review" }),
    );

    expect(await screen.findByText("Submitted")).toBeInTheDocument();
  });

  it("saves a document link and shows it once the backend accepts it", async () => {
    const club = buildClub();
    const state = serveClub(club);
    let savedLink: unknown;
    server.use(
      http.put(
        `/api${CLUB_URL}/requirements/budget/link`,
        async ({ request }) => {
          savedLink = await request.json();
          state.requirements = state.requirements.map((row) =>
            row.requirement_type === "budget"
              ? {
                  ...row,
                  status: "submitted",
                  link_url: "https://docs.example.com/budget",
                }
              : row,
          );
          return HttpResponse.json(
            state.requirements.find((row) => row.requirement_type === "budget"),
          );
        },
      ),
    );
    const { user } = await openClub(club);

    await user.click(
      within(requirementRow("Budget")).getByRole("button", {
        name: "Provide link",
      }),
    );
    await user.type(
      screen.getByLabelText(/document link/i),
      "  https://docs.example.com/budget ",
    );
    await user.click(screen.getByRole("button", { name: "Save link" }));

    expect(
      await screen.findByRole("link", {
        name: "https://docs.example.com/budget",
      }),
    ).toBeInTheDocument();
    expect(savedLink).toEqual({ link_url: "https://docs.example.com/budget" });
    expect(
      within(requirementRow("Budget")).getByText("Provided"),
    ).toBeInTheDocument();
  });

  it("explains an invalid link inline and never calls the backend", async () => {
    const club = buildClub();
    serveClub(club);
    const { user } = await openClub(club);

    await user.click(
      within(requirementRow("Budget")).getByRole("button", {
        name: "Provide link",
      }),
    );
    await user.type(screen.getByLabelText(/document link/i), "not a link");
    await user.click(screen.getByRole("button", { name: "Save link" }));

    expect(
      await screen.findByText("Enter a full link, starting with https://"),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/document link/i)).toHaveAttribute(
      "aria-invalid",
      "true",
    );
  });

  it("saves a link when Enter is pressed", async () => {
    const club = buildClub();
    serveClub(club);
    let saved = false;
    server.use(
      http.put(`/api${CLUB_URL}/requirements/budget/link`, () => {
        saved = true;
        return HttpResponse.json(buildRequirements(club.id)[2]);
      }),
    );
    const { user } = await openClub(club);

    await user.click(
      within(requirementRow("Budget")).getByRole("button", {
        name: "Provide link",
      }),
    );
    await user.type(
      screen.getByLabelText(/document link/i),
      "https://docs.example.com/budget{Enter}",
    );

    expect(await screen.findByText("Link saved")).toBeInTheDocument();
    expect(saved).toBe(true);
  });

  it("shows read-only details once the club is under review", async () => {
    const club = buildClub({ status: "under_review" });
    serveClub(club);
    await openClub(club);

    expect(
      screen.queryByRole("button", { name: /edit/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /provide link/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /approve/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /reject/i }),
    ).not.toBeInTheDocument();
  });
});

describe("club detail as an admin", () => {
  it("offers no owner controls on someone else's draft", async () => {
    const club = buildClub({ status: "drafting" });
    serveClub(club);
    await openClub(club, ADMIN);

    expect(
      screen.queryByRole("button", { name: /edit/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Submit for review" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Provide link" }),
    ).not.toBeInTheDocument();
  });

  it("offers only 'Start review' on a submitted club", async () => {
    const club = buildClub({ status: "submitted" });
    serveClub(club);
    await openClub(club, ADMIN);

    expect(
      screen.getByRole("button", { name: "Start review" }),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Submit for review" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /edit/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Approve club" }),
    ).not.toBeInTheDocument();
  });

  it("offers approve, request changes, reject and per-requirement review while under review", async () => {
    const club = buildClub({ status: "under_review" });
    const requirements = buildRequirements(CLUB_ID).map((row) =>
      row.requirement_type === "budget"
        ? row
        : {
            ...row,
            status: "submitted" as const,
            link_url: "https://example.com/doc",
          },
    );
    serveClub(club, requirements);
    await openClub(club, ADMIN);

    expect(
      screen.getByRole("button", { name: "Approve club" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Request changes" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Reject club" }),
    ).toBeInTheDocument();
    // A document with nothing provided can be rejected but not approved.
    expect(
      within(requirementRow("Budget")).queryByRole("button", {
        name: "Approve",
      }),
    ).not.toBeInTheDocument();
    expect(
      within(requirementRow("Budget")).getByRole("button", { name: "Reject" }),
    ).toBeInTheDocument();
    expect(
      within(requirementRow("Constitution")).getByRole("button", {
        name: "Approve",
      }),
    ).toBeInTheDocument();
    // Checklist items are approved by the reviewer directly.
    expect(
      within(requirementRow("Bank account setup")).getByRole("button", {
        name: "Approve",
      }),
    ).toBeInTheDocument();
  });

  it("asks for confirmation, showing the note, before rejecting the club", async () => {
    const club = buildClub({ status: "under_review" });
    const state = serveClub(club);
    let sent: unknown;
    server.use(
      http.post(`/api${CLUB_URL}/reject`, async ({ request }) => {
        sent = await request.json();
        state.club = { ...state.club, status: "rejected" };
        return HttpResponse.json(state.club);
      }),
    );
    const { user } = await openClub(club, ADMIN);

    await user.click(screen.getByRole("button", { name: "Reject club" }));
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByRole("textbox"), "Duplicate club");
    await user.click(
      within(dialog).getByRole("button", { name: "Reject club" }),
    );

    expect(within(dialog).getByText("Reject Chess Club?")).toBeInTheDocument();
    expect(
      within(dialog).getByRole("button", { name: "Yes, reject" }),
    ).toHaveFocus();
    expect(within(dialog).getByText("Duplicate club")).toBeInTheDocument();
    expect(sent).toBeUndefined();

    await user.click(
      within(dialog).getByRole("button", { name: "Yes, reject" }),
    );

    expect(await screen.findByText("Club rejected")).toBeInTheDocument();
    expect(sent).toEqual({ note: "Duplicate club" });
  });

  it("goes back to the note from the confirmation without sending", async () => {
    const club = buildClub({ status: "under_review" });
    serveClub(club);
    const { user } = await openClub(club, ADMIN);

    await user.click(screen.getByRole("button", { name: "Reject club" }));
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByRole("textbox"), "Duplicate club");
    await user.click(
      within(dialog).getByRole("button", { name: "Reject club" }),
    );
    await user.click(within(dialog).getByRole("button", { name: "Back" }));

    expect(within(dialog).getByRole("textbox")).toHaveValue("Duplicate club");
    expect(within(dialog).getByRole("textbox")).toHaveFocus();
  });

  it("stops a note at the length the backend allows", async () => {
    const club = buildClub({ status: "under_review" });
    serveClub(club);
    const { user } = await openClub(club, ADMIN);

    await user.click(screen.getByRole("button", { name: "Request changes" }));
    const note = within(await screen.findByRole("dialog")).getByRole("textbox");
    await user.click(note);
    await user.paste("a".repeat(2001));

    expect(note).toHaveValue("a".repeat(2000));
  });

  it("requires a note to request changes and sends it trimmed", async () => {
    const club = buildClub({ status: "under_review" });
    const state = serveClub(club);
    let sent: unknown;
    server.use(
      http.post(`/api${CLUB_URL}/request-changes`, async ({ request }) => {
        sent = await request.json();
        state.club = { ...state.club, status: "changes_requested" };
        return HttpResponse.json(state.club);
      }),
    );
    const { user } = await openClub(club, ADMIN);

    await user.click(screen.getByRole("button", { name: "Request changes" }));
    const dialog = await screen.findByRole("dialog");
    const confirm = within(dialog).getByRole("button", {
      name: "Request changes",
    });
    expect(confirm).toBeDisabled();

    await user.type(within(dialog).getByRole("textbox"), "   ");
    expect(confirm).toBeDisabled();

    await user.type(
      within(dialog).getByRole("textbox"),
      "Budget is missing totals  ",
    );
    await user.click(confirm);
    expect(sent).toBeUndefined();
    await user.click(
      within(dialog).getByRole("button", { name: "Yes, request changes" }),
    );

    // The new status badge and the confirmation toast.
    await waitFor(() =>
      expect(screen.getAllByText("Changes requested")).toHaveLength(2),
    );
    expect(sent).toEqual({ note: "Budget is missing totals" });
  });

  it("keeps the dialog open and shows the error when the backend refuses", async () => {
    const club = buildClub({ status: "under_review" });
    serveClub(club);
    server.use(
      http.post(`/api${CLUB_URL}/requirements/constitution/reject`, () =>
        HttpResponse.json(
          {
            detail:
              "Requirements can only be reviewed while the club is under_review",
          },
          { status: 409 },
        ),
      ),
    );
    const { user } = await openClub(club, ADMIN);

    await user.click(
      within(requirementRow("Constitution")).getByRole("button", {
        name: "Reject",
      }),
    );
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByRole("textbox"), "Unsigned");
    await user.click(within(dialog).getByRole("button", { name: "Reject" }));

    expect(
      await within(dialog).findByText(
        "Requirements can only be reviewed while the club is under_review",
      ),
    ).toBeInTheDocument();
  });
});

describe("club detail page title", () => {
  it("names the club in the browser tab", async () => {
    const club = buildClub();
    serveClub(club);
    await openClub(club);

    await waitFor(() => expect(document.title).toBe("Chess Club · Club Setup"));
  });
});

describe("club detail errors", () => {
  it("shows the backend's message when the club cannot be loaded", async () => {
    server.use(
      http.get(`/api${CLUB_URL}`, () =>
        HttpResponse.json({ detail: "Not your club" }, { status: 403 }),
      ),
      http.get(`/api${CLUB_URL}/requirements`, () =>
        HttpResponse.json({ detail: "Not your club" }, { status: 403 }),
      ),
      http.get(`/api${CLUB_URL}/events`, () =>
        HttpResponse.json({ detail: "Not your club" }, { status: 403 }),
      ),
    );
    renderApp(CLUB_URL, { signedInAs: LEAD });

    expect(await screen.findByText("Could not load club")).toBeInTheDocument();
    expect(screen.getByText("Not your club")).toBeInTheDocument();
  });
});
