export const TOKEN_KEY = "access_token";

// This module can't reach React state, so it announces a session that can't be
// refreshed and leaves the sign-out itself to the auth context.
export const SESSION_EXPIRED_EVENT = "session-expired";

// A 401 from these means the credentials themselves were rejected; trying a
// refresh would be pointless (or, for /auth/refresh, a loop).
const NO_REFRESH_PATHS = ["/auth/login", "/auth/refresh", "/auth/logout"];

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

function readDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((error) => error.msg).join(", ");
  return "Something went wrong";
}

function send(path: string, options: RequestInit): Promise<Response> {
  const headers = new Headers(options.headers);

  const token = localStorage.getItem(TOKEN_KEY);
  if (token) headers.set("Authorization", `Bearer ${token}`);

  if (typeof options.body === "string") {
    headers.set("Content-Type", "application/json");
  }

  return fetch(`/api${path}`, { ...options, headers });
}

/** Swaps the httpOnly refresh cookie for a new access token. */
async function refreshAccessToken(): Promise<boolean> {
  const response = await fetch("/api/auth/refresh", { method: "POST" });
  if (!response.ok) return false;
  const { access_token } = await response.json();
  localStorage.setItem(TOKEN_KEY, access_token);
  return true;
}

/** Sends the request with the stored token, refreshing an expired one once,
 * and throws ApiError for any failed response. */
async function request(path: string, options: RequestInit): Promise<Response> {
  let response = await send(path, options);

  const isExpiredSession =
    response.status === 401 &&
    localStorage.getItem(TOKEN_KEY) !== null &&
    !NO_REFRESH_PATHS.includes(path);
  if (isExpiredSession) {
    if (await refreshAccessToken()) {
      response = await send(path, options);
    } else {
      localStorage.removeItem(TOKEN_KEY);
      window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
    }
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, readDetail(body?.detail));
  }
  return response;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await request(path, options);
  if (response.status === 204) return undefined as T;
  return response.json();
}

/** Downloads the response as a file the browser saves under `filename`. */
export async function apiDownload(
  path: string,
  filename: string,
): Promise<void> {
  const response = await request(path, {});
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  // Revoking synchronously can cancel the download in Safari and Firefox.
  setTimeout(() => URL.revokeObjectURL(url));
}
