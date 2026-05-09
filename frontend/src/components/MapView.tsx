import { useEffect, useRef } from "react";
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
import { useGetHealthQuery, useGetPointsQuery } from "../api";
import styles from "./MapView.module.scss";

export function MapView() {
  const mapElement = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<Map | null>(null);
  const vectorLayerRef = useRef<VectorLayer<VectorSource> | null>(null);

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

  return (
    <div className={styles.mapContainer}>
      <div
        ref={mapElement}
        className={styles.map}
        aria-label="OpenStreetMap base map"
      />
      <div className={styles.apiStatus} data-state={healthStatus}>
        API {healthData?.status === "ok" ? "connected" : healthStatus}
      </div>
    </div>
  );
}
