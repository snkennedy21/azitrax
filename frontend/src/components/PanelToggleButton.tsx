import clsx from "clsx";
import { usePanelStore } from "../stores/panelStore";
import styles from "./PanelToggleButton.module.scss";

export function PanelToggleButton() {
  const isOpen = usePanelStore((state) => state.isPanelOpen);
  const togglePanel = usePanelStore((state) => state.togglePanel);

  return (
    <button
      className={styles.panelToggleButton}
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
        className={clsx(styles.icon, isOpen && styles.rotated)}
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
