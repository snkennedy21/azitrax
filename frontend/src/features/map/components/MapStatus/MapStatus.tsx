import styles from "./styles.module.scss";

type StatusItem = {
  text: string;
  state: string;
};

type MapStatusProps = {
  vessels: StatusItem & { isLoading: boolean };
  api: StatusItem;
};

export function MapStatus({ vessels, api }: MapStatusProps) {
  return (
    <div className={styles.statusStack}>
      <div
        className={styles.statusPill}
        data-loading={vessels.isLoading}
        data-state={vessels.state}
      >
        {vessels.text}
      </div>
      <div className={styles.statusPill} data-state={api.state}>
        {api.text}
      </div>
    </div>
  );
}
