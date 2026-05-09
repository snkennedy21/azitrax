import styles from "./styles.module.scss";

export function SettingsPanelContent() {
  return (
    <div className={styles.panelContent}>
      <h2>Settings Panel</h2>
      <p>Configure your application settings here.</p>
      <ul>
        <li>Theme preferences</li>
        <li>Notification settings</li>
        <li>Privacy controls</li>
      </ul>
    </div>
  );
}
