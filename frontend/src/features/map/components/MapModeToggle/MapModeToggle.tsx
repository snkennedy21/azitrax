import clsx from "clsx";
import { IoHandLeftOutline, IoLocationSharp } from "react-icons/io5";
import { useMapModeStore } from "@/store/mapModeStore";
import styles from "./styles.module.scss";

export function MapModeToggle() {
  const mode = useMapModeStore((state) => state.mode);
  const toggleMode = useMapModeStore((state) => state.toggleMode);

  const isCreateMode = mode === "createPoint";

  const handleClick = () => {
    toggleMode();
  };

  return (
    <button
      className={clsx(styles.mapModeToggle, isCreateMode && styles.active)}
      onClick={handleClick}
      aria-label={isCreateMode ? "Switch to navigate mode" : "Switch to add points mode"}
      aria-pressed={isCreateMode}
      title={isCreateMode ? "Navigate Map" : "Add Points"}
      type="button"
    >
      {isCreateMode ? (
        <IoLocationSharp size={20} aria-hidden="true" />
      ) : (
        <IoHandLeftOutline size={20} aria-hidden="true" />
      )}
    </button>
  );
}
