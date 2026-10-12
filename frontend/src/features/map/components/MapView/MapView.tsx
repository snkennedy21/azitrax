import "ol/ol.css";
import { MapStatus } from "../MapStatus/MapStatus";
import { VesselPopup } from "../VesselPopup/VesselPopup";
import { useMapData } from "../../hooks/useMapData";
import { useOpenLayersMap } from "../../hooks/useOpenLayersMap";
import styles from "./styles.module.scss";

export function MapView() {
  const { points, vessels, status } = useMapData();

  const {
    mapTargetRef,
    popupTargetRef,
    selectedVessel,
    closeVesselPopup,
  } = useOpenLayersMap({
    points,
    vessels,
  });

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
        onClose={closeVesselPopup}
      />
      <MapStatus vessels={status.vessels} api={status.api} />
    </div>
  );
}
