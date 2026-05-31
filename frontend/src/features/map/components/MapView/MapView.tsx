import { useEffect, useRef } from "react";
import Map from "ol/Map.js";
import View from "ol/View.js";
import TileLayer from "ol/layer/Tile.js";
import VectorLayer from "ol/layer/Vector.js";
import ImageTile from "ol/source/ImageTile.js";
import VectorSource from "ol/source/Vector.js";
import Feature from "ol/Feature.js";
import Point from "ol/geom/Point.js";
import { Circle as CircleStyle, Fill, RegularShape, Stroke, Style } from "ol/style.js";
import { fromLonLat } from "ol/proj.js";
import "ol/ol.css";
import {
  useGetHealthQuery,
  useGetPointsQuery,
  useGetVesselsQuery,
} from "@/services/api";
import styles from "./styles.module.scss";

export function MapView() {
  const mapElement = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<Map | null>(null);
  const vectorLayerRef = useRef<VectorLayer<VectorSource> | null>(null);
  const vesselLayerRef = useRef<VectorLayer<VectorSource> | null>(null);

  const { data: healthData, status: healthStatus } = useGetHealthQuery();
  const { data: pointsData } = useGetPointsQuery();
  const {
    data: vesselsData,
    error: vesselsError,
    isFetching: vesselsIsFetching,
    status: vesselsStatus,
  } = useGetVesselsQuery();

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

    const vesselSource = new VectorSource();
    const vesselStyle = new Style({
      image: new RegularShape({
        points: 3,
        radius: 8,
        rotation: Math.PI,
        fill: new Fill({ color: "#f97316" }),
        stroke: new Stroke({ color: "#ffffff", width: 2 }),
      }),
    });

    const vesselLayer = new VectorLayer({
      source: vesselSource,
      style: vesselStyle,
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
      layers: [tileLayer, vectorLayer, vesselLayer],
      view: new View({
        center: fromLonLat([0, 20]),
        zoom: 2,
      }),
      controls: [], // Remove all default controls (zoom buttons, attribution, etc.)
    });

    mapRef.current = map;
    vectorLayerRef.current = vectorLayer;
    vesselLayerRef.current = vesselLayer;

    return () => {
      map.setTarget(undefined);
      mapRef.current = null;
      vectorLayerRef.current = null;
      vesselLayerRef.current = null;
    };
  }, []);

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

  // Update live vessel markers separately from saved points.
  useEffect(() => {
    if (!vesselLayerRef.current || !vesselsData) {
      return;
    }

    const vesselSource = vesselLayerRef.current.getSource();
    if (!vesselSource) {
      return;
    }

    vesselSource.clear();

    const features = vesselsData.items.map((vessel) => {
      const feature = new Feature({
        geometry: new Point(fromLonLat([vessel.lon, vessel.lat])),
      });
      feature.setId(`live-vessel:${vessel.id}`);
      feature.setProperties({
        label: vessel.label,
        mmsi: vessel.mmsi,
        timestamp: vessel.timestamp,
      });
      return feature;
    });

    vesselSource.addFeatures(features);
  }, [vesselsData]);

  const vesselCount = vesselsData?.metadata.returnedCount ?? 0;
  const vesselStatusState = vesselsError ? "error" : vesselsStatus;
  const vesselsAreLoading = !vesselsError && (vesselsStatus === "pending" || vesselsIsFetching);
  let vesselStatusText = `Vessels live (${vesselCount})`;
  if (vesselsError instanceof Error) {
    vesselStatusText = `Vessels error: ${vesselsError.message}`;
  } else if (vesselsStatus === "pending") {
    vesselStatusText = "Vessels loading";
  } else if (vesselsIsFetching) {
    vesselStatusText = `Vessels refreshing (${vesselCount})`;
  }

  return (
    <div className={styles.mapContainer}>
      <div
        ref={mapElement}
        className={styles.map}
        aria-label="OpenStreetMap base map"
      />
      <div className={styles.statusStack}>
        <div
          className={styles.statusPill}
          data-loading={vesselsAreLoading}
          data-state={vesselStatusState}
        >
          {vesselStatusText}
        </div>
        <div className={styles.statusPill} data-state={healthStatus}>
          API {healthData?.status === "ok" ? "connected" : healthStatus}
        </div>
      </div>
    </div>
  );
}
