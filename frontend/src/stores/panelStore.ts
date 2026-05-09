import { create } from "zustand";
import { ReactNode } from "react";

interface PanelState {
  isPanelOpen: boolean;
  panelWidth: number;
  panelContent: ReactNode;
  setIsPanelOpen: (isOpen: boolean) => void;
  setPanelWidth: (width: number) => void;
  setPanelContent: (content: ReactNode) => void;
  togglePanel: (content?: ReactNode) => void;
}

export const usePanelStore = create<PanelState>((set) => ({
  isPanelOpen: false,
  panelWidth: 320,
  panelContent: null,
  setIsPanelOpen: (isOpen) => set({ isPanelOpen: isOpen }),
  setPanelWidth: (width) => set({ panelWidth: width }),
  setPanelContent: (content) => set({ panelContent: content }),
  togglePanel: (content) => set((state) => {
    // If panel is closed and content is provided, open with new content
    if (!state.isPanelOpen && content !== undefined) {
      return { isPanelOpen: true, panelContent: content };
    }
    // If panel is open and same content is clicked, close it
    if (state.isPanelOpen && content !== undefined && state.panelContent === content) {
      return { isPanelOpen: false };
    }
    // If panel is open and different content is clicked, just change content
    if (state.isPanelOpen && content !== undefined && state.panelContent !== content) {
      return { panelContent: content };
    }
    // Default toggle behavior
    return { isPanelOpen: !state.isPanelOpen };
  }),
}));
