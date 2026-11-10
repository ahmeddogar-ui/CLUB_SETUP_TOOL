import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll } from "vitest";
import { server } from "./server";

// jsdom has no matchMedia; the layout's mobile hook needs one. Never matching
// means tests render the desktop layout.
window.matchMedia = (query: string) =>
  ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  }) satisfies MediaQueryList;

// A request with no handler is a test failure, even when the app swallows the
// resulting network error into an error state the test never looks at.
const unhandledRequests: string[] = [];
server.events.on("request:unhandled", ({ request }) => {
  unhandledRequests.push(`${request.method} ${request.url}`);
});

beforeAll(() => server.listen({ onUnhandledFrame: "error" }));

afterEach(() => {
  cleanup();
  server.resetHandlers();
  localStorage.clear();
  const unexpected = unhandledRequests.splice(0);
  if (unexpected.length > 0) {
    throw new Error(`Unhandled requests:\n${unexpected.join("\n")}`);
  }
});

afterAll(() => server.close());
