import { useCallback, useEffect, useRef, useState } from "react";
import Feature from "ol/Feature.js";
import Map from "ol/Map.js";
import type MapBrowserEvent from "ol/MapBrowserEvent.js";
import Overlay from "ol/Overlay.js";
import View from "ol/View.js";
import Attribution from "ol/control/Attribution.js";
import Point from "ol/geom/Point.js";
import TileLayer from "ol/layer/Tile.js";
import VectorLayer from "ol/layer/Vector.js";
import { fromLonLat } from "ol/proj.js";
import ImageTile from "ol/source/ImageTile.js";
import VectorSource from "ol/source/Vector.js";
import { Circle as CircleStyle, Fill, Stroke, Style } from "ol/style.js";
import type { LiveVesselMapItem, PointListItem } from "@/services/api";
import { getVesselStyle } from "../styles/vesselStyle";

type UseOpenLayersMapOptions = {
  points?: PointListItem[];
  vessels?: LiveVesselMapItem[];
};

function getCartoBasemapApiKey(): string {
  const apiKey = import.meta.env.VITE_CARTO_BASEMAP_API_KEY?.trim();
  if (!apiKey) {
    throw new Error("VITE_CARTO_BASEMAP_API_KEY is required");
  }
  return apiKey;
}

const cartoBasemapApiKey = getCartoBasemapApiKey();

// Rebuild each OpenLayers source from the latest server snapshot.
function replacePointFeatures(layer: VectorLayer<VectorSource>, points: PointListItem[]) {
  const source = layer.getSource();
  if (!source) {
    return;
  }

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
}

function replaceVesselFeatures(layer: VectorLayer<VectorSource>, vessels: LiveVesselMapItem[]) {
  const source = layer.getSource();
  if (!source) {
    return;
  }

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
}

export function useOpenLayersMap({ points, vessels }: UseOpenLayersMapOptions) {
  // OpenLayers objects are mutable and do not belong in React state. Refs keep
  // them stable across renders without causing React to render on map changes.
  const mapTargetRef = useRef<HTMLDivElement | null>(null);
  const popupTargetRef = useRef<HTMLDivElement | null>(null);
  const pointLayerRef = useRef<VectorLayer<VectorSource> | null>(null);
  const vesselLayerRef = useRef<VectorLayer<VectorSource> | null>(null);
  const vesselPopupRef = useRef<Overlay | null>(null);
  const [selectedVesselId, setSelectedVesselId] = useState<string | null>(null);

  const selectedVessel =
    vessels?.find((vessel) => vessel.id === selectedVesselId) ?? null;

  // Create the map once, connect its imperative events to React selection,
  // and release every listener and reference when the view unmounts.
  useEffect(() => {
    if (!mapTargetRef.current) {
      return;
    }

    const pointLayer = new VectorLayer({
      source: new VectorSource(),
      style: new Style({
        image: new CircleStyle({
          radius: 6,
          fill: new Fill({ color: "#3b82f6" }),
          stroke: new Stroke({ color: "#ffffff", width: 2 }),
        }),
      }),
    });

    const vesselLayer = new VectorLayer({
      source: new VectorSource(),
      style: (feature) =>
        getVesselStyle(feature.get("course"), feature.get("freshness")),
    });

    const tileLayer = new TileLayer({
      source: new ImageTile({
        attributions:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>',
        url: `https://{a-d}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}.png?key=${encodeURIComponent(cartoBasemapApiKey)}`,
      }),
    });

    const map = new Map({
      target: mapTargetRef.current,
      layers: [tileLayer, pointLayer, vesselLayer],
      view: new View({
        center: fromLonLat([0, 20]),
        zoom: 2,
      }),
      controls: [new Attribution({ collapsible: false })],
    });

    const vesselPopup = new Overlay({
      element: popupTargetRef.current ?? undefined,
      positioning: "bottom-center",
      offset: [0, -20],
      stopEvent: true,
      autoPan: {
        animation: { duration: 200 },
        margin: 16,
      },
    });
    map.addOverlay(vesselPopup);

    const findVesselAtPixel = (event: MapBrowserEvent) =>
      map.forEachFeatureAtPixel(
        event.pixel,
        (feature, layer) =>
          layer === vesselLayer ? (feature.get("vesselId") as string | undefined) : undefined,
        { hitTolerance: 6 },
      );
    const handleMapClick = (event: MapBrowserEvent) => {
      setSelectedVesselId(findVesselAtPixel(event) ?? null);
    };
    const handlePointerMove = (event: MapBrowserEvent) => {
      map.getTargetElement().style.cursor = findVesselAtPixel(event) ? "pointer" : "";
    };

    map.on("click", handleMapClick);
    map.on("pointermove", handlePointerMove);
    pointLayerRef.current = pointLayer;
    vesselLayerRef.current = vesselLayer;
    vesselPopupRef.current = vesselPopup;

    return () => {
      map.un("click", handleMapClick);
      map.un("pointermove", handlePointerMove);
      map.getTargetElement().style.cursor = "";
      map.setTarget(undefined);
      pointLayerRef.current = null;
      vesselLayerRef.current = null;
      vesselPopupRef.current = null;
    };
  }, []);

  // Keep saved-point features synchronized with query data without recreating
  // the map or its layers.
  useEffect(() => {
    if (pointLayerRef.current && points) {
      replacePointFeatures(pointLayerRef.current, points);
    }
  }, [points]);

  // Live vessel snapshots replace the previous features. A selection is also
  // cleared here if its vessel has disappeared from the latest snapshot.
  useEffect(() => {
    if (!vesselLayerRef.current || !vessels) {
      return;
    }

    replaceVesselFeatures(vesselLayerRef.current, vessels);
    setSelectedVesselId((currentId) =>
      currentId && !vessels.some((vessel) => vessel.id === currentId) ? null : currentId,
    );
  }, [vessels]);

  // The popup is rendered by React, but positioned geographically by the
  // OpenLayers overlay whenever the selected vessel moves or changes.
  useEffect(() => {
    vesselPopupRef.current?.setPosition(
      selectedVessel ? fromLonLat([selectedVessel.lon, selectedVessel.lat]) : undefined,
    );
  }, [selectedVessel]);

  // Escape is a document-level interaction, so register it only while a
  // vessel is selected and remove it immediately when the popup closes.
  useEffect(() => {
    if (!selectedVesselId) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setSelectedVesselId(null);
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [selectedVesselId]);

  const closeVesselPopup = useCallback(() => setSelectedVesselId(null), []);

  // This is the hook's complete interface: DOM attachment points plus the
  // small amount of selection state the React view needs to render.
  return {
    mapTargetRef,
    popupTargetRef,
    selectedVessel,
    closeVesselPopup,
  };
}
