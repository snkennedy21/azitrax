import { ReactNode } from "react";
import clsx from "clsx";
import { usePanelStore } from "../stores/panelStore";
import styles from "./PanelToggleButton.module.scss";

interface PanelToggleButtonProps {
  children: ReactNode;
  content: ReactNode;
  ariaLabel?: string;
}

export function PanelToggleButton({ children, content, ariaLabel = "Toggle panel" }: PanelToggleButtonProps) {
  const isOpen = usePanelStore((state) => state.isPanelOpen);
  const panelContent = usePanelStore((state) => state.panelContent);
  const togglePanel = usePanelStore((state) => state.togglePanel);

  const isActive = isOpen && panelContent === content;

  const handleClick = () => {
    togglePanel(content);
  };

  return (
    <button
      className={clsx(styles.panelToggleButton, isActive && styles.active)}
      onClick={handleClick}
      aria-label={ariaLabel}
      aria-expanded={isActive}
      aria-pressed={isActive}
      type="button"
    >
      {children}
    </button>
  );
}
