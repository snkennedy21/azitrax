import Feature from "ol/Feature.js";
import Point from "ol/geom/Point.js";
import VectorLayer from "ol/layer/Vector.js";
import { fromLonLat } from "ol/proj.js";
import VectorSource from "ol/source/Vector.js";
import type { LiveVesselMapItem } from "@/services/api";
import { getVesselStyle } from "../../styles/vesselStyle";

export function createLiveVesselsLayer() {
  const source = new VectorSource();
  const layer = new VectorLayer({
    source,
    style: (feature) =>
      getVesselStyle(feature.get("course"), feature.get("freshness")),
  });

  return {
    layer,
    replace(vessels: LiveVesselMapItem[]) {
      source.clear();
      source.addFeatures(
        vessels.map((vessel) => {
          const feature = new Feature({
            geometry: new Point(fromLonLat([vessel.lon, vessel.lat])),
          });
          feature.setId(`live-vessel:${vessel.id}`);
          feature.setProperties({
            vesselId: vessel.id,
            label: vessel.label,
            mmsi: vessel.mmsi,
            course: vessel.course,
            freshness: vessel.freshness,
            timestamp: vessel.timestamp,
          });
          return feature;
        }),
      );
    },
  };
}
