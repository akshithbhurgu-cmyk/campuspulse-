import { useEffect, useState } from "react";

const baseUrl = (import.meta.env.VITE_API_BASE_URL || "/api").replace(
  /\/$/,
  "",
);

export async function get<T>(path: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(
    `${baseUrl}${path}${path.includes("?") ? "&" : "?"}student_id=1`,
    { signal, cache: "no-store" },
  );
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail =
      typeof body?.detail === "string"
        ? body.detail
        : `Backend returned HTTP ${response.status}`;
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export async function send<T>(
  path: string,
  method: "POST" | "PATCH" | "DELETE",
  payload: unknown,
): Promise<T> {
  const response = await fetch(
    `${baseUrl}${path}${path.includes("?") ? "&" : "?"}student_id=1`,
    {
      method,
      headers: { "Content-Type": "application/json" },
      body: method === "DELETE" ? undefined : JSON.stringify(payload),
    },
  );
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail =
      typeof body?.detail === "string"
        ? body.detail
        : "The change could not be saved.";
    throw new Error(detail);
  }
  const result = await response.json() as T;
  window.dispatchEvent(new Event("campuspulse:data-changed"));
  return result;
}

export function useApi<T>(path: string, refreshOnMutation = false) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setError(null);
    // Keep the current screen mounted during background refreshes. Clearing it
    // every 15 seconds made forms disappear mid-edit and caused visible flicker.
    const isInitialLoad = data === null;
    if (isInitialLoad) setLoading(true);
    get<T>(path, controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) setData(value);
      })
      .catch((reason) => {
        if (!controller.signal.aborted)
          setError(
            reason instanceof Error ? reason.message : "Unable to load data",
          );
      })
      .finally(() => {
        if (!controller.signal.aborted && isInitialLoad) setLoading(false);
      });
    return () => controller.abort();
  }, [path, revision]);
  useEffect(() => {
    const refresh = () => setRevision((value) => value + 1);
    if (refreshOnMutation) {
      window.addEventListener("campuspulse:data-changed", refresh);
    }
    const interval = window.setInterval(refresh, 15000);
    return () => {
      if (refreshOnMutation) {
        window.removeEventListener("campuspulse:data-changed", refresh);
      }
      window.clearInterval(interval);
    };
  }, [refreshOnMutation]);
  return {
    data,
    error,
    loading,
    retry: () => setRevision((value) => value + 1),
  };
}
