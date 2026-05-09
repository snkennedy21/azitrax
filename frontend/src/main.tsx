import { StrictMode, useState } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SidePanel } from "./components/SidePanel";
import { PanelToggleButton } from "./components/PanelToggleButton";
import { MapView } from "./components/MapView";
import "./styles.css";

const queryClient = new QueryClient();

function App() {
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [panelWidth, setPanelWidth] = useState(320);

  return (
    <div className="app-layout">
      <SidePanel
        isOpen={isPanelOpen}
        width={panelWidth}
        onWidthChange={setPanelWidth}
      >
        <PanelToggleButton
          isOpen={isPanelOpen}
          onClick={() => setIsPanelOpen(!isPanelOpen)}
        />
      </SidePanel>
      <MapView />
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
