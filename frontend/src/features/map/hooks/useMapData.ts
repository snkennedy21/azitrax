import {
  useGetHealthQuery,
  useGetPointsQuery,
  useGetVesselsQuery,
} from "@/services/api";

export function useMapData() {
  const { data: healthData, status: healthStatus } = useGetHealthQuery();
  const { data: points } = useGetPointsQuery();
  const {
    data: vesselsData,
    error: vesselsError,
    isFetching: vesselsAreFetching,
    status: vesselsStatus,
  } = useGetVesselsQuery();

  const vesselCount = vesselsData?.metadata.returnedCount ?? 0;
  const vesselsAreLoading = !vesselsError &&
    (vesselsStatus === "pending" || vesselsAreFetching);
  let vesselStatusText = `Vessels live (${vesselCount})`;
  if (vesselsError instanceof Error) {
    vesselStatusText = `Vessels error: ${vesselsError.message}`;
  } else if (vesselsStatus === "pending") {
    vesselStatusText = "Vessels loading";
  } else if (vesselsAreFetching) {
    vesselStatusText = `Vessels refreshing (${vesselCount})`;
  }

  return {
    points,
    vessels: vesselsData?.items,
    status: {
      vessels: {
        text: vesselStatusText,
        state: vesselsError ? "error" : vesselsStatus,
        isLoading: vesselsAreLoading,
      },
      api: {
        text: `API ${healthData?.status === "ok" ? "connected" : healthStatus}`,
        state: healthStatus,
      },
    },
  };
}
