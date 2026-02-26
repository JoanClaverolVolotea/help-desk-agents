const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

function apiBaseUrl(): string {
  return import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL;
}

export function buildApiUrl(path: string): string {
  return `${apiBaseUrl()}${path}`;
}

export async function requestJson<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(buildApiUrl(path), {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!response.ok) {
    let payloadText = "Request failed.";
    try {
      const body = await response.json();
      payloadText = JSON.stringify(body);
    } catch {
      payloadText = await response.text();
    }
    throw new Error(payloadText);
  }

  return (await response.json()) as T;
}

export async function readErrorResponse(response: Response): Promise<string> {
  let payloadText = "Request failed.";
  try {
    const body = await response.json();
    payloadText = JSON.stringify(body);
  } catch {
    payloadText = await response.text();
  }
  return payloadText;
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
