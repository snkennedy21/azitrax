interface PanelToggleButtonProps {
  isOpen: boolean;
  onClick: () => void;
}

export function PanelToggleButton({ isOpen, onClick }: PanelToggleButtonProps) {
  return (
    <button
      className="panel-toggle-button"
      onClick={onClick}
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
