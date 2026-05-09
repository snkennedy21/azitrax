import { useQuery } from "@tanstack/react-query";
import { apiBaseUrl } from "../config";
import type { HealthResponse, Point } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: {
      Accept: "application/json",
      ...init?.headers,
    },
    ...init,
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<T>;
}

export function useGetHealthQuery() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => request<HealthResponse>("/health"),
    refetchOnWindowFocus: false,
    retry: 1,
  });
}

export function useGetPointsQuery() {
  return useQuery({
    queryKey: ["points"],
    queryFn: () => request<Point[]>("/points"),
    refetchOnWindowFocus: false,
    retry: 1,
  });
}
