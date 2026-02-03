import cronstrue from 'cronstrue';
import { Cron } from 'croner';

export function cronToHuman(expression: string): string {
  try {
    return cronstrue.toString(expression);
  } catch (error) {
    return 'Invalid cron expression';
  }
}

export function getNextRun(cronExpression: string): Date | null {
  try {
    const job = new Cron(cronExpression);
    const next = job.nextRun();
    job.stop();
    return next instanceof Date ? next : null;
  } catch (error) {
    return null;
  }
}

export function formatNextRun(cronExpression: string): string {
  const next = getNextRun(cronExpression);
  if (!next) return 'Unable to calculate';

  const now = new Date();
  const diff = next.getTime() - now.getTime();

  if (diff < 60000) return 'In less than a minute';
  if (diff < 3600000) return `In ${Math.floor(diff / 60000)} minutes`;
  if (diff < 86400000) return `In ${Math.floor(diff / 3600000)} hours`;

  return next.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}
