import {
  buildRequestDetail,
  buildRequestEvent,
  LEAD,
  ROOM,
} from "@/test/builders";
import { renderApp } from "@/test/render-app";
import { server } from "@/test/server";
import { screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

const NEW_REQUEST_URL = "/clubs/10/requests/new";

/** Serves the create endpoint and the detail page the form then opens. */
function serveCreate() {
  const state: { body?: unknown } = {};
  const created = buildRequestDetail({ id: 77, title: "Tournament boards" });
  server.use(
    http.post("/api/clubs/10/requests", async ({ request }) => {
      state.body = await request.json();
      return HttpResponse.json(created, { status: 201 });
    }),
    http.get("/api/requests/77", () => HttpResponse.json(created)),
    http.get("/api/requests/77/events", () =>
      HttpResponse.json([buildRequestEvent()]),
    ),
  );
  return state;
}

function serveRooms() {
  server.use(http.get("/api/rooms", () => HttpResponse.json([ROOM])));
}

describe("new funding request", () => {
  it("totals the line items live and saves the amounts as cents", async () => {
    const state = serveCreate();
    const { user } = renderApp(NEW_REQUEST_URL, { signedInAs: LEAD });
    await screen.findByRole("heading", { name: "New request" });

    await user.type(screen.getByLabelText(/^Title/), "Tournament boards");
    await user.type(screen.getByLabelText("Description"), "Chess boards");
    await user.type(screen.getByLabelText(/^Amount/), "125.50");
    await user.click(screen.getByRole("button", { name: "Add line item" }));
    const [, secondDescription] = screen.getAllByLabelText("Description");
    const [, secondAmount] = screen.getAllByLabelText(/^Amount/);
    await user.type(secondDescription, "Clocks");
    await user.type(secondAmount, "50");

    expect(screen.getByText("$175.50")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Save draft" }));

    expect(
      await screen.findByText("Request saved as a draft"),
    ).toBeInTheDocument();
    expect(state.body).toEqual({
      title: "Tournament boards",
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

  it("shows an inline error for a bad amount and does not save", async () => {
    const state = serveCreate();
    const { user } = renderApp(NEW_REQUEST_URL, { signedInAs: LEAD });
    await screen.findByRole("heading", { name: "New request" });

    await user.type(screen.getByLabelText(/^Title/), "Tournament boards");
    await user.type(screen.getByLabelText("Description"), "Chess boards");
    await user.type(screen.getByLabelText(/^Amount/), "12.345");
    await user.click(screen.getByRole("button", { name: "Save draft" }));

    expect(
      await screen.findByText("Enter dollars and cents, like 125.50"),
    ).toBeInTheDocument();
    expect(state.body).toBeUndefined();
  });

  it("requires a title and a description", async () => {
    const state = serveCreate();
    const { user } = renderApp(NEW_REQUEST_URL, { signedInAs: LEAD });
    await screen.findByRole("heading", { name: "New request" });

    await user.click(screen.getByRole("button", { name: "Save draft" }));

    expect(await screen.findByText("Title is required")).toBeInTheDocument();
    expect(screen.getByText("Description is required")).toBeInTheDocument();
    expect(state.body).toBeUndefined();
  });

  it("keeps at least one line item", async () => {
    const { user } = renderApp(NEW_REQUEST_URL, { signedInAs: LEAD });
    await screen.findByRole("heading", { name: "New request" });

    expect(
      screen.getByRole("button", { name: "Remove line item 1" }),
    ).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Add line item" }));
    await user.click(
      screen.getByRole("button", { name: "Remove line item 2" }),
    );

    expect(screen.getAllByLabelText("Description")).toHaveLength(1);
  });
});

describe("new room booking request", () => {
  it("lists the rooms and saves the times as ISO timestamps", async () => {
    serveRooms();
    const state = serveCreate();
    const { user } = renderApp(NEW_REQUEST_URL, { signedInAs: LEAD });
    await screen.findByRole("heading", { name: "New request" });

    await user.click(screen.getByRole("radio", { name: /Room booking/ }));
    await user.type(screen.getByLabelText(/^Title/), "Club night");
    await user.selectOptions(
      await screen.findByLabelText(/^Room \*/),
      "DV 2074 — Davis (30)",
    );
    await user.type(screen.getByLabelText(/^Date/), "2030-01-15");
    await user.type(screen.getByLabelText(/^Start time/), "14:00");
    await user.type(screen.getByLabelText(/^End time/), "16:30");
    await user.click(screen.getByRole("button", { name: "Save draft" }));

    expect(
      await screen.findByText("Request saved as a draft"),
    ).toBeInTheDocument();
    expect(state.body).toEqual({
      title: "Club night",
      details: {
        request_type: "room_booking",
        room_id: ROOM.id,
        starts_at: new Date("2030-01-15T14:00").toISOString(),
        ends_at: new Date("2030-01-15T16:30").toISOString(),
      },
    });
  });

  it("shows an inline error when the end is before the start", async () => {
    serveRooms();
    const state = serveCreate();
    const { user } = renderApp(NEW_REQUEST_URL, { signedInAs: LEAD });
    await screen.findByRole("heading", { name: "New request" });

    await user.click(screen.getByRole("radio", { name: /Room booking/ }));
    await user.type(screen.getByLabelText(/^Title/), "Club night");
    await user.selectOptions(
      await screen.findByLabelText(/^Room \*/),
      "DV 2074 — Davis (30)",
    );
    await user.type(screen.getByLabelText(/^Date/), "2030-01-15");
    await user.type(screen.getByLabelText(/^Start time/), "16:00");
    await user.type(screen.getByLabelText(/^End time/), "14:00");
    await user.click(screen.getByRole("button", { name: "Save draft" }));

    expect(
      await screen.findByText("End time must be after the start time"),
    ).toBeInTheDocument();
    expect(state.body).toBeUndefined();
  });

  it("limits a booking to 12 hours", async () => {
    serveRooms();
    const state = serveCreate();
    const { user } = renderApp(NEW_REQUEST_URL, { signedInAs: LEAD });
    await screen.findByRole("heading", { name: "New request" });

    await user.click(screen.getByRole("radio", { name: /Room booking/ }));
    await user.type(screen.getByLabelText(/^Title/), "Club night");
    await user.selectOptions(
      await screen.findByLabelText(/^Room \*/),
      "DV 2074 — Davis (30)",
    );
    await user.type(screen.getByLabelText(/^Date/), "2030-01-15");
    await user.type(screen.getByLabelText(/^Start time/), "06:00");
    await user.type(screen.getByLabelText(/^End time/), "20:00");
    await user.click(screen.getByRole("button", { name: "Save draft" }));

    expect(
      await screen.findByText("A booking can be at most 12 hours"),
    ).toBeInTheDocument();
    expect(state.body).toBeUndefined();
  });
});
