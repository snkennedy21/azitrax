import { create } from "zustand";

export type MapMode = "navigate" | "createPoint";

interface MapModeState {
  mode: MapMode;
  setMode: (mode: MapMode) => void;
  toggleMode: () => void;
}

export const useMapModeStore = create<MapModeState>((set) => ({
  mode: "navigate",
  setMode: (mode) => set({ mode }),
  toggleMode: () =>
    set((state) => ({
      mode: state.mode === "navigate" ? "createPoint" : "navigate",
    })),
}));
