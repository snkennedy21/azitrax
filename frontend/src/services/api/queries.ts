import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiBaseUrl } from "../config";
import type {
  HealthResponse,
  PointListItem,
  PointCreate,
  PointResponse,
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

export function useCreatePointMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: PointCreate) =>
      request<PointResponse>("/points", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["points"] });
    },
  });
}
