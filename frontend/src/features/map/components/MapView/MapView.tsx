import "ol/ol.css";
import { useState } from "react";
import { MapStatus } from "../MapStatus/MapStatus";
import { VesselPopup } from "../VesselPopup/VesselPopup";
import { useMapData } from "../../hooks/useMapData";
import { useOpenLayersMap } from "../../hooks/useOpenLayersMap";
import styles from "./styles.module.scss";

export function MapView() {
  const [selectedVesselId, setSelectedVesselId] = useState<string | null>(null);
  const {
    points,
    vessels,
    vesselHistoryIsFetching,
    fetchVesselHistory,
    status,
  } = useMapData(selectedVesselId);

  const {
    mapTargetRef,
    popupTargetRef,
    selectedVessel,
    closeVesselPopup,
  } = useOpenLayersMap({
    points,
    vessels,
    selectedVesselId,
    onSelectedVesselIdChange: setSelectedVesselId,
  });

  const handleLoadVesselHistory = () => {
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
