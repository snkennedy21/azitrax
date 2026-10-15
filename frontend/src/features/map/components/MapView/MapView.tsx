import "ol/ol.css";
import { useCallback, useState } from "react";
import { MapStatus } from "../MapStatus/MapStatus";
import { VesselPopup } from "../VesselPopup/VesselPopup";
import { useMapData } from "../../hooks/useMapData";
import { useOpenLayersMap } from "../../hooks/useOpenLayersMap";
import styles from "./styles.module.scss";

export function MapView() {
  const [selectedVesselId, setSelectedVesselId] = useState<string | null>(null);
  const [historyIsVisible, setHistoryIsVisible] = useState(false);
  const {
    points,
    vessels,
    vesselHistory,
    vesselHistoryIsFetching,
    fetchVesselHistory,
    status,
  } = useMapData(selectedVesselId);

  const handleSelectedVesselIdChange = useCallback((vesselId: string | null) => {
    setHistoryIsVisible(false);
    setSelectedVesselId(vesselId);
  }, []);

  const {
    mapTargetRef,
    popupTargetRef,
    selectedVessel,
    closeVesselPopup,
  } = useOpenLayersMap({
    points,
    vessels,
    vesselHistory: historyIsVisible ? vesselHistory : undefined,
    selectedVesselId,
    onSelectedVesselIdChange: handleSelectedVesselIdChange,
  });

  const handleLoadVesselHistory = () => {
    setHistoryIsVisible(true);
    void fetchVesselHistory();
  };

  return (
    <div className={styles.mapContainer}>
      <div
        ref={mapTargetRef}
        className={styles.map}
        aria-label="OpenStreetMap base map"
      />
      <VesselPopup
        ref={popupTargetRef}
        vessel={selectedVessel}
        historyIsFetching={vesselHistoryIsFetching}
        onLoadHistory={handleLoadVesselHistory}
        onClose={closeVesselPopup}
      />
      <MapStatus vessels={status.vessels} api={status.api} />
    </div>
  );
}
