import { useEffect, useRef, useState } from "react";
import Map from "ol/Map.js";
import Overlay from "ol/Overlay.js";
import View from "ol/View.js";
import Attribution from "ol/control/Attribution.js";
import TileLayer from "ol/layer/Tile.js";
import VectorLayer from "ol/layer/Vector.js";
import ImageTile from "ol/source/ImageTile.js";
import VectorSource from "ol/source/Vector.js";
import Feature from "ol/Feature.js";
import Point from "ol/geom/Point.js";
import { Circle as CircleStyle, Fill, Icon, Stroke, Style } from "ol/style.js";
import { fromLonLat } from "ol/proj.js";
import "ol/ol.css";
import vesselMarkerUrl from "@/assets/vessel-marker.svg";
import {
  useGetHealthQuery,
  useGetPointsQuery,
  useGetVesselsQuery,
} from "@/services/api";
import styles from "./styles.module.scss";

function getCartoBasemapApiKey(): string {
  const apiKey = import.meta.env.VITE_CARTO_BASEMAP_API_KEY?.trim();
  if (!apiKey) {
    throw new Error("VITE_CARTO_BASEMAP_API_KEY is required");
  }
  return apiKey;
}

const cartoBasemapApiKey = getCartoBasemapApiKey();
const vesselStyleCache: Record<string, Style> = {};

function getVesselStyle(course: unknown): Style {
  const courseDegrees = typeof course === "number" && Number.isFinite(course) ? course : 0;
  const normalizedCourse = ((courseDegrees % 360) + 360) % 360;
  const cacheKey = String(normalizedCourse);

  vesselStyleCache[cacheKey] ??= new Style({
    image: new Icon({
      src: vesselMarkerUrl,
      anchor: [0.5, 0.5],
      anchorXUnits: "fraction",
      anchorYUnits: "fraction",
      rotation: normalizedCourse * (Math.PI / 180),
      rotateWithView: true,
    }),
  });

  return vesselStyleCache[cacheKey];
}

export function MapView() {
  const mapElement = useRef<HTMLDivElement | null>(null);
  const popupElement = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<Map | null>(null);
  const vesselPopupRef = useRef<Overlay | null>(null);
  const vectorLayerRef = useRef<VectorLayer<VectorSource> | null>(null);
  const vesselLayerRef = useRef<VectorLayer<VectorSource> | null>(null);
  const [selectedVesselId, setSelectedVesselId] = useState<string | null>(null);

  const { data: healthData, status: healthStatus } = useGetHealthQuery();
  const { data: pointsData } = useGetPointsQuery();
  const {
    data: vesselsData,
    error: vesselsError,
    isFetching: vesselsIsFetching,
    status: vesselsStatus,
  } = useGetVesselsQuery();

  console.log('vesselsData: ', vesselsData)

  const selectedVessel =
    vesselsData?.items.find((vessel) => vessel.id === selectedVesselId) ?? null;

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

    const vesselLayer = new VectorLayer({
      source: vesselSource,
      style: (feature) => getVesselStyle(feature.get("course")),
    });

    const tileLayer = new TileLayer({
      source: new ImageTile({
        attributions:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>',
        url: `https://{a-d}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}.png?key=${encodeURIComponent(cartoBasemapApiKey)}`,
      }),
    });

    const map = new Map({
      target: mapElement.current,
      layers: [tileLayer, vectorLayer, vesselLayer],
      view: new View({
        center: fromLonLat([0, 20]),
        zoom: 2,
      }),
      controls: [new Attribution({ collapsible: false })],
    });

    const vesselPopup = new Overlay({
      element: popupElement.current ?? undefined,
      positioning: "bottom-center",
      offset: [0, -20],
      stopEvent: true,
      autoPan: {
        animation: { duration: 200 },
        margin: 16,
      },
    });
    map.addOverlay(vesselPopup);

    const handleMapClick = (event: { pixel: number[] }) => {
      const vesselId = map.forEachFeatureAtPixel(
        event.pixel,
        (feature, layer) =>
          layer === vesselLayer ? (feature.get("vesselId") as string | undefined) : undefined,
        { hitTolerance: 6 },
      );
      setSelectedVesselId(vesselId ?? null);
    };

    const handlePointerMove = (event: { pixel: number[] }) => {
      const isOverVessel = map.forEachFeatureAtPixel(
        event.pixel,
        (_feature, layer) => layer === vesselLayer,
        { hitTolerance: 6 },
      );
      map.getTargetElement().style.cursor = isOverVessel ? "pointer" : "";
    };

    map.on("click", handleMapClick);
    map.on("pointermove", handlePointerMove);

    mapRef.current = map;
    vesselPopupRef.current = vesselPopup;
    vectorLayerRef.current = vectorLayer;
    vesselLayerRef.current = vesselLayer;

    return () => {
      map.un("click", handleMapClick);
      map.un("pointermove", handlePointerMove);
      map.setTarget(undefined);
      mapRef.current = null;
      vesselPopupRef.current = null;
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
        vesselId: vessel.id,
        label: vessel.label,
        mmsi: vessel.mmsi,
        course: vessel.course,
        timestamp: vessel.timestamp,
      });
      return feature;
    });

    vesselSource.addFeatures(features);
  }, [vesselsData]);

  useEffect(() => {
    if (!vesselPopupRef.current) {
      return;
    }

    vesselPopupRef.current.setPosition(
      selectedVessel ? fromLonLat([selectedVessel.lon, selectedVessel.lat]) : undefined,
    );
  }, [selectedVessel]);

  useEffect(() => {
    if (selectedVesselId && vesselsData && !selectedVessel) {
      setSelectedVesselId(null);
    }
  }, [selectedVessel, selectedVesselId, vesselsData]);

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
      <div
        ref={popupElement}
        className={styles.vesselPopup}
        role="dialog"
        aria-label={selectedVessel ? `Details for ${selectedVessel.label ?? "vessel"}` : undefined}
        aria-hidden={!selectedVessel}
      >
        {selectedVessel && (
          <>
            <div className={styles.vesselPopupHeader}>
              <strong>{selectedVessel.label?.trim() || "Unknown vessel"}</strong>
              <button
                className={styles.vesselPopupClose}
                type="button"
                aria-label="Close vessel details"
                onClick={() => setSelectedVesselId(null)}
              >
                &times;
              </button>
            </div>
            <dl className={styles.vesselDetails}>
              <div>
                <dt>MMSI</dt>
                <dd>{selectedVessel.mmsi ?? "Unavailable"}</dd>
              </div>
              <div>
                <dt>Speed</dt>
                <dd>{selectedVessel.speed == null ? "Unavailable" : `${selectedVessel.speed} kn`}</dd>
              </div>
              <div>
                <dt>Course</dt>
                <dd>
                  {selectedVessel.course == null
                    ? "Unavailable"
                    : `${Math.round(selectedVessel.course)}°`}
                </dd>
              </div>
              {selectedVessel.destination?.trim() && (
                <div>
                  <dt>Destination</dt>
                  <dd>{selectedVessel.destination}</dd>
                </div>
              )}
            </dl>
            <div className={styles.vesselFreshness} data-freshness={selectedVessel.freshness}>
              {selectedVessel.freshness ?? "Unknown"}
            </div>
          </>
        )}
      </div>
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
