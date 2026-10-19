import Feature from "ol/Feature.js";
import LineString from "ol/geom/LineString.js";
import VectorLayer from "ol/layer/Vector.js";
import { fromLonLat } from "ol/proj.js";
import VectorSource from "ol/source/Vector.js";
import { Stroke, Style } from "ol/style.js";
import type { PointListItem } from "@/services/api";

export function createVesselTrailLayer() {
  const source = new VectorSource();
  const layer = new VectorLayer({
    source,
    style: new Style({
      stroke: new Stroke({ color: "#38bdf8", width: 3 }),
    }),
  });

  return {
    layer,
    replace(points: PointListItem[]) {
      source.clear();
      if (points.length < 2) {
        return;
      }

      source.addFeature(
        new Feature({
          geometry: new LineString(
            points.map((point) => fromLonLat([point.lon, point.lat])),
          ),
        }),
      );
    },
  };
}
