export const TOKEN_KEY = "access_token";

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

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  let response = await send(path, options);

  const isExpiredSession =
    response.status === 401 &&
    localStorage.getItem(TOKEN_KEY) !== null &&
    !NO_REFRESH_PATHS.includes(path);
  if (isExpiredSession && (await refreshAccessToken())) {
    response = await send(path, options);
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, readDetail(body?.detail));
  }

  if (response.status === 204) return undefined as T;
  return response.json();
}
