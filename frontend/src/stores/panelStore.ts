import { create } from "zustand";

interface PanelState {
  isPanelOpen: boolean;
  panelWidth: number;
  setIsPanelOpen: (isOpen: boolean) => void;
  setPanelWidth: (width: number) => void;
  togglePanel: () => void;
}

export const usePanelStore = create<PanelState>((set) => ({
  isPanelOpen: false,
  panelWidth: 320,
  setIsPanelOpen: (isOpen) => set({ isPanelOpen: isOpen }),
  setPanelWidth: (width) => set({ panelWidth: width }),
  togglePanel: () => set((state) => ({ isPanelOpen: !state.isPanelOpen })),
}));
