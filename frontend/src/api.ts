import { useQuery } from "@tanstack/react-query";
import { apiBaseUrl } from "./config";

export type HealthResponse = {
  status: string;
};

export type Point = {
  id: number;
  lat: number;
  lon: number;
};

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

function useGetHealthQuery() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => request<HealthResponse>("/health"),
    refetchOnWindowFocus: false,
    retry: 1,
  });
}

function useGetPointsQuery() {
  return useQuery({
    queryKey: ["points"],
    queryFn: () => request<Point[]>("/points"),
    refetchOnWindowFocus: false,
    retry: 1,
  });
}

export { useGetHealthQuery, useGetPointsQuery };
