import { server } from "@/test/server";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { ApiError, apiFetch, TOKEN_KEY } from "./api";

function captureRequest() {
  const captured: { request?: Request } = {};
  server.use(
    http.all("/api/echo", ({ request }) => {
      captured.request = request;
      return HttpResponse.json({ ok: true });
    }),
  );
  return captured;
}

function respondWith(status: number, body: string | object) {
  server.use(
    http.get("/api/echo", () =>
      typeof body === "string"
        ? new HttpResponse(body, { status })
        : HttpResponse.json(body, { status }),
    ),
  );
}

describe("apiFetch", () => {
  it("prefixes /api and returns the parsed JSON body", async () => {
    captureRequest();
    await expect(apiFetch("/echo")).resolves.toEqual({ ok: true });
  });

  it("sends the stored token as a bearer token", async () => {
    localStorage.setItem(TOKEN_KEY, "abc123");
    const captured = captureRequest();

    await apiFetch("/echo");

    expect(captured.request?.headers.get("Authorization")).toBe(
      "Bearer abc123",
    );
  });

  it("sends no Authorization header when signed out", async () => {
    const captured = captureRequest();

    await apiFetch("/echo");

    expect(captured.request?.headers.has("Authorization")).toBe(false);
  });

  it("marks string bodies as JSON", async () => {
    const captured = captureRequest();

    await apiFetch("/echo", { method: "POST", body: JSON.stringify({ a: 1 }) });

    expect(captured.request?.headers.get("Content-Type")).toBe(
      "application/json",
    );
  });

  it("leaves form bodies form-encoded, which /auth/login requires", async () => {
    const captured = captureRequest();

    await apiFetch("/echo", {
      method: "POST",
      body: new URLSearchParams({ username: "a@b.co" }),
    });

    expect(captured.request?.headers.get("Content-Type")).toMatch(
      /^application\/x-www-form-urlencoded/,
    );
  });

  it("throws ApiError carrying the status and the backend's detail string", async () => {
    respondWith(409, { detail: "missing: budget, constitution" });

    const error = await apiFetch("/echo").catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 409,
      message: "missing: budget, constitution",
    });
  });

  it("joins FastAPI validation errors into one message", async () => {
    respondWith(422, {
      detail: [
        { loc: ["body", "link_url"], msg: "Input should be a valid URL" },
        { loc: ["body", "note"], msg: "Field required" },
      ],
    });

    await expect(apiFetch("/echo")).rejects.toThrow(
      "Input should be a valid URL, Field required",
    );
  });

  it("falls back to a generic message when the error body is not JSON", async () => {
    respondWith(502, "<html>Bad Gateway</html>");

    await expect(apiFetch("/echo")).rejects.toMatchObject({
      status: 502,
      message: "Something went wrong",
    });
  });
});
