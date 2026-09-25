import type { HealthState, IncidentState, CheckStatus } from '../types';

export function formatDateTime(isoString: string | null | undefined): string {
  if (!isoString) return '—';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return isoString;
    return d.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
      timeZone: 'UTC',
    }) + ' UTC';
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
    return { text: 'Never seen', seconds: null, status: 'none' };
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

export interface BadgeStyle {
  label: string;
  bg: string;
  text: string;
  border: string;
  dot: string;
}

export function getHealthBadgeStyle(state: HealthState): BadgeStyle {
  switch (state) {
    case 'HEALTHY':
      return {
        label: 'HEALTHY',
        bg: 'bg-emerald-950/40',
        text: 'text-emerald-400',
        border: 'border-emerald-600/30',
        dot: 'bg-emerald-400',
      };
    case 'WARNING':
      return {
        label: 'WARNING',
        bg: 'bg-amber-950/40',
        text: 'text-amber-400',
        border: 'border-amber-600/30',
        dot: 'bg-amber-400',
      };
    case 'STALE':
      return {
        label: 'STALE',
        bg: 'bg-rose-950/40',
        text: 'text-rose-400',
        border: 'border-rose-600/30',
        dot: 'bg-rose-400',
      };
    case 'RECOVERING':
      return {
        label: 'RECOVERING',
        bg: 'bg-cyan-950/40',
        text: 'text-cyan-400',
        border: 'border-cyan-600/30',
        dot: 'bg-cyan-400',
      };
    case 'FAILED':
      return {
        label: 'FAILED',
        bg: 'bg-red-950/60',
        text: 'text-red-300',
        border: 'border-red-600/50',
        dot: 'bg-red-500',
      };
    default:
      return {
        label: state,
        bg: 'bg-gray-800',
        text: 'text-gray-300',
        border: 'border-gray-700',
        dot: 'bg-gray-400',
      };
  }
}

export function getIncidentStateBadgeStyle(state: IncidentState): BadgeStyle {
  switch (state) {
    case 'DETECTED':
      return {
        label: 'DETECTED',
        bg: 'bg-yellow-950/40',
        text: 'text-yellow-400',
        border: 'border-yellow-600/30',
        dot: 'bg-yellow-400',
      };
    case 'OPEN':
      return {
        label: 'OPEN',
        bg: 'bg-orange-950/40',
        text: 'text-orange-400',
        border: 'border-orange-600/30',
        dot: 'bg-orange-400',
      };
    case 'INVESTIGATING':
      return {
        label: 'INVESTIGATING',
        bg: 'bg-blue-950/40',
        text: 'text-blue-400',
        border: 'border-blue-600/30',
        dot: 'bg-blue-400',
      };
    case 'RECOVERING':
      return {
        label: 'RECOVERING',
        bg: 'bg-cyan-950/40',
        text: 'text-cyan-400',
        border: 'border-cyan-600/30',
        dot: 'bg-cyan-400',
      };
    case 'VERIFIED':
      return {
        label: 'VERIFIED',
        bg: 'bg-teal-950/40',
        text: 'text-teal-400',
        border: 'border-teal-600/30',
        dot: 'bg-teal-400',
      };
    case 'RESOLVED':
      return {
        label: 'RESOLVED',
        bg: 'bg-emerald-950/40',
        text: 'text-emerald-400',
        border: 'border-emerald-600/30',
        dot: 'bg-emerald-400',
      };
    case 'FAILED':
      return {
        label: 'FAILED',
        bg: 'bg-red-950/50',
        text: 'text-red-400',
        border: 'border-red-600/30',
        dot: 'bg-red-400',
      };
    case 'ESCALATED':
      return {
        label: 'ESCALATED',
        bg: 'bg-purple-950/50',
        text: 'text-purple-300',
        border: 'border-purple-600/40',
        dot: 'bg-purple-400',
      };
    default:
      return {
        label: state,
        bg: 'bg-gray-800',
        text: 'text-gray-300',
        border: 'border-gray-700',
        dot: 'bg-gray-400',
      };
  }
}

export function getCheckStatusStyle(status: CheckStatus): {
  label: string;
  bg: string;
  text: string;
  border: string;
} {
  switch (status) {
    case 'PASS':
      return {
        label: 'PASS',
        bg: 'rgba(16, 185, 129, 0.15)',
        text: '#34d399',
        border: '1px solid rgba(16, 185, 129, 0.3)',
      };
    case 'FAIL':
      return {
        label: 'FAIL',
        bg: 'rgba(239, 68, 68, 0.15)',
        text: '#f87171',
        border: '1px solid rgba(239, 68, 68, 0.3)',
      };
    case 'UNKNOWN':
    default:
      return {
        label: 'UNKNOWN',
        bg: 'rgba(156, 163, 175, 0.1)',
        text: '#9ca3af',
        border: '1px solid rgba(156, 163, 175, 0.2)',
      };
  }
}
