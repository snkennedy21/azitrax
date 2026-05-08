import { StrictMode, useEffect, useRef } from "react";
import { createRoot } from "react-dom/client";
import Map from "ol/Map.js";
import View from "ol/View.js";
import TileLayer from "ol/layer/Tile.js";
import OSM from "ol/source/OSM.js";
import { fromLonLat } from "ol/proj.js";
import "ol/ol.css";
import "./styles.css";

function App() {
  const mapElement = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!mapElement.current) {
      return;
    }

    const map = new Map({
      target: mapElement.current,
      layers: [
        new TileLayer({
          source: new OSM(),
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

  return <div ref={mapElement} className="map" aria-label="OpenStreetMap base map" />;
}

const root = document.getElementById("root");

if (!root) {
  throw new Error("Root element not found");
}

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
