import styles from "./PanelContent.module.scss";

export function InfoPanelContent() {
  return (
    <div className={styles.panelContent}>
      <h2>Information Panel</h2>
      <p>View important information about your map.</p>
      <div>
        <strong>Map Details:</strong>
        <ul>
          <li>Zoom level: 12</li>
          <li>Center: [0, 0]</li>
          <li>Layers: 3 active</li>
        </ul>
      </div>
    </div>
  );
}
