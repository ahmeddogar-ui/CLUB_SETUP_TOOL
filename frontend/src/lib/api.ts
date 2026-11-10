export const TOKEN_KEY = "access_token";

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

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);

  const token = localStorage.getItem(TOKEN_KEY);
  if (token) headers.set("Authorization", `Bearer ${token}`);

  if (typeof options.body === "string") {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`/api${path}`, { ...options, headers });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new ApiError(response.status, readDetail(body?.detail));
  }

  return response.json();
}
