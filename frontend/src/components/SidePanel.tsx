import { ReactNode, useCallback, useEffect, useRef } from "react";

interface SidePanelProps {
  isOpen: boolean;
  width: number;
  onWidthChange: (width: number) => void;
  children?: ReactNode;
}

const MIN_WIDTH = 320;
const MAX_WIDTH_PERCENT = 50;

export function SidePanel({ isOpen, width, onWidthChange, children }: SidePanelProps) {
  const isResizingRef = useRef(false);
  const startXRef = useRef(0);
  const startWidthRef = useRef(0);
  const panelRef = useRef<HTMLElement>(null);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isResizingRef.current = true;
    startXRef.current = e.clientX;
    startWidthRef.current = width;
    document.body.style.cursor = "ew-resize";
    document.body.style.userSelect = "none";

    // Disable transition during resize
    if (panelRef.current) {
      panelRef.current.style.transition = "none";
    }
  }, [width]);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizingRef.current) return;

      const delta = e.clientX - startXRef.current;
      const newWidth = startWidthRef.current + delta;
      const maxWidth = (window.innerWidth * MAX_WIDTH_PERCENT) / 100;

      const constrainedWidth = Math.min(Math.max(newWidth, MIN_WIDTH), maxWidth);
      onWidthChange(constrainedWidth);
    };

    const handleMouseUp = () => {
      if (!isResizingRef.current) return;

      isResizingRef.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";

      // Re-enable transition after resize
      if (panelRef.current) {
        panelRef.current.style.transition = "";
      }
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [onWidthChange]);

  return (
    <aside
      ref={panelRef}
      className={`side-panel ${isOpen ? "side-panel--open" : ""}`}
      style={{ width: isOpen ? `${width}px` : 0 }}
    >
      {children}
      <div className="side-panel__content" style={{ width: `${width}px` }}>
        {!children && (
          <div className="side-panel__placeholder">
            <p>Panel content will go here</p>
          </div>
        )}
      </div>
      {isOpen && (
        <div
          className="side-panel__resize-handle"
          onMouseDown={handleMouseDown}
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize panel"
        />
      )}
    </aside>
  );
}
