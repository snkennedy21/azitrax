import { useCallback, useEffect, useRef } from "react";
import Map from "ol/Map.js";
import type { default as MapBrowserEvent } from "ol/MapBrowserEvent.js";
import View from "ol/View.js";
import TileLayer from "ol/layer/Tile.js";
import VectorLayer from "ol/layer/Vector.js";
import ImageTile from "ol/source/ImageTile.js";
import VectorSource from "ol/source/Vector.js";
import Feature from "ol/Feature.js";
import Point from "ol/geom/Point.js";
import { Circle as CircleStyle, Fill, Stroke, Style } from "ol/style.js";
import { fromLonLat, toLonLat } from "ol/proj.js";
import "ol/ol.css";
import {
  useGetHealthQuery,
  useGetPointsQuery,
  useCreatePointMutation,
} from "@/services/api";
import { useMapModeStore } from "@/store/mapModeStore";
import { MapModeToggle } from "../MapModeToggle/MapModeToggle";
import styles from "./styles.module.scss";

export function MapView() {
  const mapElement = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<Map | null>(null);
  const vectorLayerRef = useRef<VectorLayer<VectorSource> | null>(null);

  const { data: healthData, status: healthStatus } = useGetHealthQuery();
  const { data: pointsData } = useGetPointsQuery();
  const createPointMutation = useCreatePointMutation();
  const mode = useMapModeStore((state) => state.mode);

  // Click handler - defined as component function with fresh values
  const handleMapClick = useCallback(
    (event: MapBrowserEvent) => {
      // Only create points if in createPoint mode
      if (mode !== "createPoint") {
        return;
      }

      // Prevent rapid clicks while mutation is pending
      if (createPointMutation.isPending) {
        return;
      }

      // Get clicked coordinates (in EPSG:3857 Web Mercator)
      const clickedCoordinate = event.coordinate;

      // Convert to WGS84 (EPSG:4326) lon/lat
      const [lon, lat] = toLonLat(clickedCoordinate);

      // Call mutation to create point
      createPointMutation.mutate({ lat, lon });
    },
    [mode, createPointMutation],
  );

  // Set Up Map
  useEffect(() => {
    if (!mapElement.current) {
      return;
    }

    const vectorSource = new VectorSource();
    const vectorStyle = new Style({
      image: new CircleStyle({
        radius: 6,
        fill: new Fill({ color: "#3b82f6" }),
        stroke: new Stroke({ color: "#ffffff", width: 2 }),
      }),
    });

    const vectorLayer = new VectorLayer({
      source: vectorSource,
      style: vectorStyle,
    });

    const tileLayer = new TileLayer({
      source: new ImageTile({
        attributions:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>',
        url: "https://{a-d}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
      }),
    });

    const map = new Map({
      target: mapElement.current,
      layers: [tileLayer, vectorLayer],
      view: new View({
        center: fromLonLat([0, 20]),
        zoom: 2,
      }),
      controls: [], // Remove all default controls (zoom buttons, attribution, etc.)
    });

    mapRef.current = map;
    vectorLayerRef.current = vectorLayer;

    return () => {
      map.setTarget(undefined);
      mapRef.current = null;
      vectorLayerRef.current = null;
    };
  }, []);

  // Attach/detach click handler when it changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map) {
      return;
    }

    map.on("singleclick", handleMapClick);

    return () => {
      map.un("singleclick", handleMapClick);
    };
  }, [handleMapClick]);

  // Update Map When pointsData Changes
  useEffect(() => {
    if (!vectorLayerRef.current || !pointsData) {
      return;
    }

    const vectorSource = vectorLayerRef.current.getSource();
    if (!vectorSource) {
      return;
    }

    vectorSource.clear();

    const features = pointsData.map((point) => {
      const feature = new Feature({
        geometry: new Point(fromLonLat([point.lon, point.lat])),
      });
      feature.setId(point.id);
      return feature;
    });

    vectorSource.addFeatures(features);
  }, [pointsData]);

  return (
    <div className={styles.mapContainer}>
      <div
        ref={mapElement}
        className={styles.map}
        data-cursor-mode={mode}
        aria-label="OpenStreetMap base map"
      />
      <MapModeToggle />
      <div className={styles.apiStatus} data-state={healthStatus}>
        API {healthData?.status === "ok" ? "connected" : healthStatus}
      </div>
    </div>
  );
}
