import { StrictMode, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import Map from "ol/Map.js";
import View from "ol/View.js";
import TileLayer from "ol/layer/Tile.js";
import VectorLayer from "ol/layer/Vector.js";
import ImageTile from "ol/source/ImageTile.js";
import VectorSource from "ol/source/Vector.js";
import Feature from "ol/Feature.js";
import Point from "ol/geom/Point.js";
import { Circle as CircleStyle, Fill, Stroke, Style } from "ol/style.js";
import { fromLonLat } from "ol/proj.js";
import "ol/ol.css";
import { useGetHealthQuery, useGetPointsQuery } from "./api";
import { SidePanel } from "./components/SidePanel";
import { PanelToggleButton } from "./components/PanelToggleButton";
import "./styles.css";

const queryClient = new QueryClient();

function App() {
  const mapElement = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<Map | null>(null);
  const vectorLayerRef = useRef<VectorLayer<VectorSource> | null>(null);
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [panelWidth, setPanelWidth] = useState(320);

  // Queries
  const { data: healthData, status: healthStatus } = useGetHealthQuery();
  const { data: pointsData } = useGetPointsQuery();

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
    });

    mapRef.current = map;
    vectorLayerRef.current = vectorLayer;

    return () => {
      map.setTarget(undefined);
      mapRef.current = null;
      vectorLayerRef.current = null;
    };
  }, []);

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

  // Update map size when panel opens/closes
  useEffect(() => {
    if (!mapRef.current) {
      return;
    }

    // Use setTimeout to ensure CSS transition completes before updating size
    const timeoutId = setTimeout(() => {
      mapRef.current?.updateSize();
    }, 300); // Match CSS transition duration

    return () => clearTimeout(timeoutId);
  }, [isPanelOpen]);

  return (
    <div className="app-layout">
      <SidePanel
        isOpen={isPanelOpen}
        width={panelWidth}
        onWidthChange={setPanelWidth}
      />
      <div className="map-container">
        <PanelToggleButton
          isOpen={isPanelOpen}
          onClick={() => setIsPanelOpen(!isPanelOpen)}
        />
        <div
          ref={mapElement}
          className="map"
          aria-label="OpenStreetMap base map"
        />
        <div className="api-status" data-state={healthStatus}>
          API {healthData?.status === "ok" ? "connected" : healthStatus}
        </div>
      </div>
    </div>
  );
}

const root = document.getElementById("root");

if (!root) {
  throw new Error("Root element not found");
}

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
);
