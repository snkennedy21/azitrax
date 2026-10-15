import { useQuery } from "@tanstack/react-query";
import { apiBaseUrl } from "../config";
import type {
  HealthResponse,
  PointListItem,
  LiveVesselsResponse,
} from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: {
      Accept: "application/json",
      ...init?.headers,
    },
    ...init,
  });

  if (!response.ok) {
    throw new Error(
      `API request failed: ${response.status} ${response.statusText}`,
    );
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
    queryFn: () => request<PointListItem[]>("/points"),
    refetchOnWindowFocus: false,
    retry: 1,
  });
}

export function useGetVesselsQuery() {
  return useQuery({
    queryKey: ["vessels"],
    queryFn: () => request<LiveVesselsResponse>("/live/vessels"),
    refetchInterval: 10000,
    refetchOnWindowFocus: false,
    retry: 1,
  });
}

export function useGetVesselHistoryQuery(mmsi: number | null) {
  return useQuery({
    queryKey: ["vessel-history", mmsi],
    queryFn: () => {
      if (mmsi === null) {
        throw new Error("MMSI is required to request vessel history");
      }

      return request<PointListItem[]>(`/vessels/${mmsi}/history`);
    },
    enabled: false,
    refetchOnWindowFocus: false,
    retry: 1,
  });
}
