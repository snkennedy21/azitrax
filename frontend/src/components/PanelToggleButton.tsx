import { usePanelStore } from "../stores/panelStore";

export function PanelToggleButton() {
  const isOpen = usePanelStore((state) => state.isPanelOpen);
  const togglePanel = usePanelStore((state) => state.togglePanel);

  return (
    <button
      className="panel-toggle-button"
      onClick={togglePanel}
      aria-label={isOpen ? "Close panel" : "Open panel"}
      aria-expanded={isOpen}
      type="button"
    >
      <svg
        width="20"
        height="20"
        viewBox="0 0 20 20"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={`panel-toggle-button__icon ${isOpen ? "panel-toggle-button__icon--rotated" : ""}`}
      >
        <path
          d="M7 4L13 10L7 16"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </button>
  );
}
