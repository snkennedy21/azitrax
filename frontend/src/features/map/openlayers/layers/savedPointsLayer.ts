import Feature from "ol/Feature.js";
import Point from "ol/geom/Point.js";
import VectorLayer from "ol/layer/Vector.js";
import { fromLonLat } from "ol/proj.js";
import VectorSource from "ol/source/Vector.js";
import { Circle as CircleStyle, Fill, Stroke, Style } from "ol/style.js";
import type { PointListItem } from "@/services/api";

export function createSavedPointsLayer() {
  const source = new VectorSource();
  const layer = new VectorLayer({
    source,
    style: new Style({
      image: new CircleStyle({
        radius: 6,
        fill: new Fill({ color: "#3b82f6" }),
        stroke: new Stroke({ color: "#ffffff", width: 2 }),
      }),
    }),
  });

  return {
    layer,
    replace(points: PointListItem[]) {
      source.clear();
      source.addFeatures(
        points.map((point) => {
          const feature = new Feature({
            geometry: new Point(fromLonLat([point.lon, point.lat])),
          });
          feature.setId(point.id);
          return feature;
        }),
      );
    },
  };
}
