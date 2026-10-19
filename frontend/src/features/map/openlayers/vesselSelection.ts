import type { EventsKey } from "ol/events.js";
import Map from "ol/Map.js";
import type MapBrowserEvent from "ol/MapBrowserEvent.js";
import Overlay from "ol/Overlay.js";
import type VectorLayer from "ol/layer/Vector.js";
import { unByKey } from "ol/Observable.js";
import { fromLonLat } from "ol/proj.js";
import type VectorSource from "ol/source/Vector.js";
import type { LiveVesselMapItem } from "@/services/api";

type VesselSelectionOptions = {
  map: Map;
  vesselLayer: VectorLayer<VectorSource>;
  popupElement: HTMLElement;
  onVesselSelected: (vesselId: string | null) => void;
};

export function createVesselSelection({
  map,
  vesselLayer,
  popupElement,
  onVesselSelected,
}: VesselSelectionOptions) {
  const popup = new Overlay({
    element: popupElement,
    positioning: "bottom-center",
    offset: [0, -20],
    stopEvent: true,
    autoPan: {
      animation: { duration: 200 },
      margin: 16,
    },
  });
  map.addOverlay(popup);

  let escapeListenerIsActive = false;

  const findVesselAtPixel = (event: MapBrowserEvent) =>
    map.forEachFeatureAtPixel(
      event.pixel,
      (feature, layer) =>
        layer === vesselLayer
          ? (feature.get("vesselId") as string | undefined)
          : undefined,
      { hitTolerance: 6 },
    );

  const handleMapClick = (event: MapBrowserEvent) => {
    onVesselSelected(findVesselAtPixel(event) ?? null);
  };
  const handlePointerMove = (event: MapBrowserEvent) => {
    map.getTargetElement().style.cursor = findVesselAtPixel(event) ? "pointer" : "";
  };
  const handleKeyDown = (event: KeyboardEvent) => {
    if (event.key === "Escape") {
      onVesselSelected(null);
    }
  };

  const listenerKeys: EventsKey[] = [
    map.on("click", handleMapClick),
    map.on("pointermove", handlePointerMove),
  ];

  const setEscapeListenerIsActive = (shouldBeActive: boolean) => {
    if (shouldBeActive === escapeListenerIsActive) {
      return;
    }

    escapeListenerIsActive = shouldBeActive;
    if (shouldBeActive) {
      document.addEventListener("keydown", handleKeyDown);
    } else {
      document.removeEventListener("keydown", handleKeyDown);
    }
  };

  return {
    update(vessel: LiveVesselMapItem | null) {
      popup.setPosition(
        vessel ? fromLonLat([vessel.lon, vessel.lat]) : undefined,
      );
      setEscapeListenerIsActive(vessel !== null);
    },
    destroy() {
      setEscapeListenerIsActive(false);
      unByKey(listenerKeys);
      map.getTargetElement().style.cursor = "";
      map.removeOverlay(popup);
    },
  };
}
