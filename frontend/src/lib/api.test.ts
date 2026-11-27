import { server } from "@/test/server";
import { http, HttpResponse } from "msw";
import { describe, expect, it, onTestFinished, vi } from "vitest";
import {
  ApiError,
  apiDownload,
  apiFetch,
  SESSION_EXPIRED_EVENT,
  TOKEN_KEY,
} from "./api";

function listenForSessionExpiry() {
  const listener = vi.fn();
  window.addEventListener(SESSION_EXPIRED_EVENT, listener);
  onTestFinished(() =>
    window.removeEventListener(SESSION_EXPIRED_EVENT, listener),
  );
  return listener;
}

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

  it("returns undefined for 204 No Content", async () => {
    server.use(
      http.post("/api/echo", () => new HttpResponse(null, { status: 204 })),
    );
    await expect(
      apiFetch("/echo", { method: "POST" }),
    ).resolves.toBeUndefined();
  });

  describe("when the access token has expired", () => {
    function expireTokenUntilRefreshed() {
      const seenTokens: (string | null)[] = [];
      server.use(
        http.get("/api/echo", ({ request }) => {
          const header = request.headers.get("Authorization");
          seenTokens.push(header);
          return header === "Bearer fresh"
            ? HttpResponse.json({ ok: true })
            : HttpResponse.json({ detail: "Expired" }, { status: 401 });
        }),
      );
      return seenTokens;
    }

    it("refreshes once and retries with the new token", async () => {
      localStorage.setItem(TOKEN_KEY, "stale");
      const seenTokens = expireTokenUntilRefreshed();
      server.use(
        http.post("/api/auth/refresh", () =>
          HttpResponse.json({ access_token: "fresh", token_type: "bearer" }),
        ),
      );

      await expect(apiFetch("/echo")).resolves.toEqual({ ok: true });
      expect(seenTokens).toEqual(["Bearer stale", "Bearer fresh"]);
      expect(localStorage.getItem(TOKEN_KEY)).toBe("fresh");
    });

    it("gives up with the original 401 when the refresh is refused", async () => {
      localStorage.setItem(TOKEN_KEY, "stale");
      const seenTokens = expireTokenUntilRefreshed();
      server.use(
        http.post("/api/auth/refresh", () =>
          HttpResponse.json(
            { detail: "Invalid refresh token" },
            { status: 401 },
          ),
        ),
      );

      await expect(apiFetch("/echo")).rejects.toMatchObject({ status: 401 });
      expect(seenTokens).toEqual(["Bearer stale"]);
    });

    it("ends the session when the refresh is refused", async () => {
      localStorage.setItem(TOKEN_KEY, "stale");
      expireTokenUntilRefreshed();
      server.use(
        http.post("/api/auth/refresh", () =>
          HttpResponse.json(
            { detail: "Invalid refresh token" },
            { status: 401 },
          ),
        ),
      );
      const sessionExpired = listenForSessionExpiry();

      await expect(apiFetch("/echo")).rejects.toMatchObject({ status: 401 });
      expect(localStorage.getItem(TOKEN_KEY)).toBeNull();
      expect(sessionExpired).toHaveBeenCalledOnce();
    });

    it("does not try to refresh when nobody is signed in", async () => {
      // No refresh handler: an attempt would fail the test as an unhandled request.
      expireTokenUntilRefreshed();
      await expect(apiFetch("/echo")).rejects.toMatchObject({ status: 401 });
    });

    it("does not try to refresh or end the session on a rejected login", async () => {
      localStorage.setItem(TOKEN_KEY, "stale");
      const sessionExpired = listenForSessionExpiry();
      server.use(
        http.post("/api/auth/login", () =>
          HttpResponse.json(
            { detail: "Incorrect email or password" },
            { status: 401 },
          ),
        ),
      );
      await expect(
        apiFetch("/auth/login", {
          method: "POST",
          body: new URLSearchParams(),
        }),
      ).rejects.toMatchObject({ status: 401 });
      expect(sessionExpired).not.toHaveBeenCalled();
    });
  });
});

describe("apiDownload", () => {
  function stubObjectUrls() {
    const createObjectURL = vi.fn(() => "blob:clubs");
    const revokeObjectURL = vi.fn();
    // jsdom has neither, so they're assigned (not spied) and left in place.
    Object.assign(URL, { createObjectURL, revokeObjectURL });
    return { createObjectURL, revokeObjectURL };
  }

  function captureClickedLink() {
    const clicked: HTMLAnchorElement[] = [];
    const click = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(function (this: HTMLAnchorElement) {
        clicked.push(this);
      });
    onTestFinished(() => click.mockRestore());
    return clicked;
  }

  it("saves the response as a file with the given name, then frees the URL", async () => {
    const { createObjectURL, revokeObjectURL } = stubObjectUrls();
    const clicked = captureClickedLink();
    localStorage.setItem(TOKEN_KEY, "abc123");
    let authorization: string | null = null;
    server.use(
      http.get("/api/echo", ({ request }) => {
        authorization = request.headers.get("Authorization");
        return new HttpResponse("id,name\n", {
          headers: { "Content-Type": "text/csv" },
        });
      }),
    );

    await apiDownload("/echo", "clubs.csv");

    expect(authorization).toBe("Bearer abc123");
    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(clicked).toHaveLength(1);
    expect(clicked[0].download).toBe("clubs.csv");
    expect(clicked[0].href).toBe("blob:clubs");
    // Freed after the click has been handled, not during it.
    expect(revokeObjectURL).not.toHaveBeenCalled();
    await vi.waitFor(() =>
      expect(revokeObjectURL).toHaveBeenCalledWith("blob:clubs"),
    );
  });

  it("throws ApiError and saves nothing when the request fails", async () => {
    const { createObjectURL } = stubObjectUrls();
    respondWith(403, { detail: "Admin access required" });

    await expect(apiDownload("/echo", "clubs.csv")).rejects.toMatchObject({
      status: 403,
      message: "Admin access required",
    });
    expect(createObjectURL).not.toHaveBeenCalled();
  });

  it("refreshes an expired token once and retries", async () => {
    stubObjectUrls();
    captureClickedLink();
    localStorage.setItem(TOKEN_KEY, "stale");
    const seenTokens: (string | null)[] = [];
    server.use(
      http.get("/api/echo", ({ request }) => {
        const header = request.headers.get("Authorization");
        seenTokens.push(header);
        return header === "Bearer fresh"
          ? new HttpResponse("id\n")
          : HttpResponse.json({ detail: "Expired" }, { status: 401 });
      }),
      http.post("/api/auth/refresh", () =>
        HttpResponse.json({ access_token: "fresh", token_type: "bearer" }),
      ),
    );

    await apiDownload("/echo", "clubs.csv");

    expect(seenTokens).toEqual(["Bearer stale", "Bearer fresh"]);
  });
});
