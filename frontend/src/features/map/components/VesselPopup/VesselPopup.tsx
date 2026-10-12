import { forwardRef } from "react";
import type { LiveVesselMapItem } from "@/services/api";
import styles from "./styles.module.scss";

type VesselPopupProps = {
  vessel: LiveVesselMapItem | null;
  onClose: () => void;
};

export const VesselPopup = forwardRef<HTMLDivElement, VesselPopupProps>(
  function VesselPopup({ vessel, onClose }, ref) {
    return (
      <div
        ref={ref}
        className={styles.vesselPopup}
        role="dialog"
        aria-label={vessel ? `Details for ${vessel.label ?? "vessel"}` : undefined}
        aria-hidden={!vessel}
      >
        {vessel && (
          <>
            <div className={styles.header}>
              <strong>{vessel.label?.trim() || "Unknown vessel"}</strong>
              <button
                className={styles.closeButton}
                type="button"
                aria-label="Close vessel details"
                onClick={onClose}
              >
                &times;
              </button>
            </div>
            <dl className={styles.details}>
              <div>
                <dt>MMSI</dt>
                <dd>{vessel.mmsi ?? "Unavailable"}</dd>
              </div>
              <div>
                <dt>Speed</dt>
                <dd>{vessel.speed == null ? "Unavailable" : `${vessel.speed} kn`}</dd>
              </div>
              <div>
                <dt>Course</dt>
                <dd>{vessel.course == null ? "Unavailable" : `${Math.round(vessel.course)}°`}</dd>
              </div>
              {vessel.destination?.trim() && (
                <div>
                  <dt>Destination</dt>
                  <dd>{vessel.destination}</dd>
                </div>
              )}
            </dl>
            <div className={styles.freshness} data-freshness={vessel.freshness}>
              {vessel.freshness ?? "Unknown"}
            </div>
          </>
        )}
      </div>
    );
  },
);
