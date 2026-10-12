import Icon from "ol/style/Icon.js";
import Style from "ol/style/Style.js";
import vesselMarkerSvg from "@/assets/vessel-marker.svg?raw";

const vesselStyleCache: Record<string, Style> = {};
const vesselMarkerUrls = {
  fresh: createVesselMarkerUrl("#22c55e"),
  stale: createVesselMarkerUrl("#f97316"),
};

function createVesselMarkerUrl(fillColor: string): string {
  const coloredSvg = vesselMarkerSvg.replace("#f97316", fillColor);
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(coloredSvg)}`;
}

export function getVesselStyle(course: unknown, freshness: unknown): Style {
  const courseDegrees = typeof course === "number" && Number.isFinite(course) ? course : 0;
  const normalizedCourse = ((courseDegrees % 360) + 360) % 360;
  const freshnessKey = freshness === "fresh" ? "fresh" : "stale";
  const cacheKey = `${freshnessKey}:${normalizedCourse}`;

  vesselStyleCache[cacheKey] ??= new Style({
    image: new Icon({
      src: vesselMarkerUrls[freshnessKey],
      anchor: [0.5, 0.5],
      anchorXUnits: "fraction",
      anchorYUnits: "fraction",
      rotation: normalizedCourse * (Math.PI / 180),
      rotateWithView: true,
    }),
  });

  return vesselStyleCache[cacheKey];
}
