import { setupServer } from "msw/node";

// Started and reset by setup.ts. Tests register the endpoints they need with
// server.use(...), so each test states the backend responses it depends on.
export const server = setupServer();
