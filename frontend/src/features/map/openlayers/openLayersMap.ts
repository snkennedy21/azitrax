import Map from "ol/Map.js";
import View from "ol/View.js";
import Attribution from "ol/control/Attribution.js";
import { fromLonLat } from "ol/proj.js";
import type { LiveVesselMapItem, PointListItem } from "@/services/api";
import { createBasemapLayer } from "./layers/basemapLayer";
import { createLiveVesselsLayer } from "./layers/liveVesselsLayer";
import { createSavedPointsLayer } from "./layers/savedPointsLayer";
import { createVesselTrailLayer } from "./layers/vesselTrailLayer";
import { createVesselSelection } from "./vesselSelection";

type CreateOpenLayersMapOptions = {
  target: HTMLElement;
  popupElement: HTMLElement;
  basemapApiKey: string;
  onVesselSelected: (vesselId: string | null) => void;
};

export type OpenLayersMapController = {
  replacePoints(points: PointListItem[]): void;
  replaceVessels(vessels: LiveVesselMapItem[]): void;
  replaceVesselTrail(points: PointListItem[]): void;
  updateSelectedVessel(vessel: LiveVesselMapItem | null): void;
  destroy(): void;
};

export function createOpenLayersMap({
  target,
  popupElement,
  basemapApiKey,
  onVesselSelected,
}: CreateOpenLayersMapOptions): OpenLayersMapController {
  const basemapLayer = createBasemapLayer(basemapApiKey);
  const savedPoints = createSavedPointsLayer();
  const vesselTrail = createVesselTrailLayer();
  const liveVessels = createLiveVesselsLayer();

  const map = new Map({
    target,
    layers: [
      basemapLayer,
      savedPoints.layer,
      vesselTrail.layer,
      liveVessels.layer,
    ],
    view: new View({
      center: fromLonLat([0, 20]),
      zoom: 2,
    }),
    controls: [new Attribution({ collapsible: false })],
  });

  const vesselSelection = createVesselSelection({
    map,
    vesselLayer: liveVessels.layer,
    popupElement,
    onVesselSelected,
  });

  return {
    replacePoints: savedPoints.replace,
    replaceVessels: liveVessels.replace,
    replaceVesselTrail: vesselTrail.replace,
    updateSelectedVessel: vesselSelection.update,
    destroy() {
      vesselSelection.destroy();
      map.setTarget(undefined);
    },
  };
}
