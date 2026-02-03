import SystemPulse from '@/components/dashboard/SystemPulse';
import MetricSparklines from '@/components/dashboard/MetricSparklines';
import ActivityStream from '@/components/dashboard/ActivityStream';
import styles from './page.module.css';

export default function DashboardPage() {
  return (
    <div className={styles.container}>
      <h1 className={styles.pageTitle}>Dashboard</h1>

      <div className={styles.grid}>
        {/* System Health Monitoring */}
        <div className={styles.fullWidth}>
          <SystemPulse />
        </div>

        {/* Metrics Statistics */}
        <div className={styles.fullWidth}>
          <MetricSparklines />
        </div>

        {/* Activity Stream */}
        <div className={styles.fullWidth}>
          <ActivityStream />
        </div>
      </div>
    </div>
  );
}
