import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { IoSettings, IoInformationCircle } from "react-icons/io5";
import { MapView } from "./features/map";
import {
  SidePanel,
  PanelToggleButton,
  InfoPanelContent,
  SettingsPanelContent,
} from "./features/panels";
import "./styles/global.scss";

const queryClient = new QueryClient();

function App() {
  console.log("Render");
  return (
    <div className="app-layout">
      <SidePanel>
        <PanelToggleButton
          content={<SettingsPanelContent />}
          ariaLabel="Toggle settings panel"
        >
          <IoSettings size={20} />
        </PanelToggleButton>
        <PanelToggleButton
          content={<InfoPanelContent />}
          ariaLabel="Toggle information panel"
        >
          <IoInformationCircle size={20} />
        </PanelToggleButton>
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
