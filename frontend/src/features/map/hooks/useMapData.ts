import {
  useGetHealthQuery,
  useGetPointsQuery,
  useGetVesselHistoryQuery,
  useGetVesselsQuery,
} from "@/services/api";

export function useMapData(selectedVesselId: string | null) {
  const { data: healthData, status: healthStatus } = useGetHealthQuery();
  const { data: points } = useGetPointsQuery();
  const {
    data: vesselsData,
    error: vesselsError,
    isFetching: vesselsAreFetching,
    status: vesselsStatus,
  } = useGetVesselsQuery();
  const selectedVessel = vesselsData?.items.find(
    (vessel) => vessel.id === selectedVesselId,
  );
  const {
    data: vesselHistory,
    isFetching: vesselHistoryIsFetching,
    refetch: fetchVesselHistory,
  } = useGetVesselHistoryQuery(selectedVessel?.mmsi ?? null);

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
    vesselHistory,
    vesselHistoryIsFetching,
    fetchVesselHistory,
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
