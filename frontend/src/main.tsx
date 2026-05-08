import { StrictMode, useEffect, useRef } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import Map from "ol/Map.js";
import View from "ol/View.js";
import TileLayer from "ol/layer/Tile.js";
import ImageTile from "ol/source/ImageTile.js";
import { fromLonLat } from "ol/proj.js";
import "ol/ol.css";
import { getHealth } from "./api";
import "./styles.css";

const queryClient = new QueryClient();

function App() {
  const mapElement = useRef<HTMLDivElement | null>(null);
  const healthQuery = useQuery({
    queryKey: ["health"],
    queryFn: getHealth,
    refetchOnWindowFocus: false,
    retry: 1,
  });

  useEffect(() => {
    if (!mapElement.current) {
      return;
    }

    const map = new Map({
      target: mapElement.current,
      layers: [
        new TileLayer({
          source: new ImageTile({
            attributions:
              '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>',
            url: "https://{a-d}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
          }),
        }),
      ],
      view: new View({
        center: fromLonLat([-73.9857, 40.7484]),
        zoom: 12,
      }),
    });

    return () => {
      map.setTarget(undefined);
    };
  }, []);

  return (
    <>
      <div ref={mapElement} className="map" aria-label="OpenStreetMap base map" />
      <div className="api-status" data-state={healthQuery.status}>
        API {healthQuery.data?.status === "ok" ? "connected" : healthQuery.status}
      </div>
    </>
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
