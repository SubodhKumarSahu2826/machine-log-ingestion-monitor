import type { CheckStatus } from '../types';

export function formatDateTime(isoString: string | null | undefined): string {
  if (!isoString) return '—';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    return (
      d.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
        timeZone: 'UTC',
      }) + ' UTC'
    );
  } catch {
    return isoString;
  }
}

export function calculateFreshnessSeconds(lastSeenAt: string | null | undefined): number | null {
  if (!lastSeenAt) return null;
  const d = new Date(lastSeenAt);
  if (isNaN(d.getTime())) return null;
  const now = new Date();
  return Math.max(0, Math.floor((now.getTime() - d.getTime()) / 1000));
}

export function formatFreshness(lastSeenAt: string | null | undefined): {
  text: string;
  seconds: number | null;
  status: 'fresh' | 'warning' | 'stale' | 'none';
} {
  const seconds = calculateFreshnessSeconds(lastSeenAt);
  if (seconds === null) {
    return { text: 'No events', seconds: null, status: 'none' };
  }
  if (seconds < 60) {
    return { text: `${seconds}s ago`, seconds, status: 'fresh' };
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  if (minutes < 60) {
    return {
      text: `${minutes}m ${remainingSeconds}s ago`,
      seconds,
      status: seconds >= 120 ? 'stale' : 'warning',
    };
  }
  const hours = Math.floor(minutes / 60);
  return { text: `${hours}h ${minutes % 60}m ago`, seconds, status: 'stale' };
}

export function getCheckStatusStyle(status: CheckStatus): {
  label: string;
  className: string;
  symbol: string;
} {
  switch (status) {
    case 'PASS':
      return { label: 'PASS', className: 'check-pass', symbol: '✓' };
    case 'FAIL':
      return { label: 'FAIL', className: 'check-fail', symbol: '✕' };
    case 'UNKNOWN':
    default:
      return { label: 'UNKNOWN', className: 'check-unknown', symbol: '—' };
  }
}
