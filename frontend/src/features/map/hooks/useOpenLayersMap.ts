import { useCallback, useEffect, useRef } from "react";
import type { LiveVesselMapItem, PointListItem } from "@/services/api";
import {
  createOpenLayersMap,
  type OpenLayersMapController,
} from "../openlayers/openLayersMap";

type UseOpenLayersMapOptions = {
  points?: PointListItem[];
  vessels?: LiveVesselMapItem[];
  vesselHistory?: PointListItem[];
  selectedVesselId: string | null;
  onSelectedVesselIdChange: (vesselId: string | null) => void;
};

function getCartoBasemapApiKey(): string {
  const apiKey = import.meta.env.VITE_CARTO_BASEMAP_API_KEY?.trim();
  if (!apiKey) {
    throw new Error("VITE_CARTO_BASEMAP_API_KEY is required");
  }
  return apiKey;
}

const cartoBasemapApiKey = getCartoBasemapApiKey();

export function useOpenLayersMap({
  points,
  vessels,
  vesselHistory,
  selectedVesselId,
  onSelectedVesselIdChange,
}: UseOpenLayersMapOptions) {
  const mapTargetRef = useRef<HTMLDivElement | null>(null);
  const popupTargetRef = useRef<HTMLDivElement | null>(null);
  const mapControllerRef = useRef<OpenLayersMapController | null>(null);
  const selectionChangeRef = useRef(onSelectedVesselIdChange);

  const selectedVessel =
    vessels?.find((vessel) => vessel.id === selectedVesselId) ?? null;

  useEffect(() => {
    selectionChangeRef.current = onSelectedVesselIdChange;
  }, [onSelectedVesselIdChange]);

  // The OpenLayers object graph has one lifetime: mount it after React attaches
  // both DOM targets, then release all listeners and targets on unmount.
  useEffect(() => {
    if (!mapTargetRef.current || !popupTargetRef.current) {
      return;
    }

    const controller = createOpenLayersMap({
      target: mapTargetRef.current,
      popupElement: popupTargetRef.current,
      basemapApiKey: cartoBasemapApiKey,
      onVesselSelected: (vesselId) => selectionChangeRef.current(vesselId),
    });
    mapControllerRef.current = controller;

    return () => {
      controller.destroy();
      mapControllerRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (points) {
      mapControllerRef.current?.replacePoints(points);
    }
  }, [points]);

  useEffect(() => {
    if (vessels) {
      mapControllerRef.current?.replaceVessels(vessels);
    }
  }, [vessels]);

  useEffect(() => {
    mapControllerRef.current?.replaceVesselTrail(vesselHistory ?? []);
  }, [vesselHistory]);

  useEffect(() => {
    mapControllerRef.current?.updateSelectedVessel(selectedVessel);
  }, [selectedVessel]);

  // Selection validity is React state policy, independent of rendering the
  // vessel snapshot into OpenLayers.
  useEffect(() => {
    if (
      selectedVesselId &&
      vessels &&
      !vessels.some((vessel) => vessel.id === selectedVesselId)
    ) {
      selectionChangeRef.current(null);
    }
  }, [selectedVesselId, vessels]);

  const closeVesselPopup = useCallback(() => {
    selectionChangeRef.current(null);
  }, []);

  return {
    mapTargetRef,
    popupTargetRef,
    selectedVessel,
    closeVesselPopup,
  };
}
