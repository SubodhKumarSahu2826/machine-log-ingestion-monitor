import React from 'react';
import type { HealthState, IncidentState } from '../types';

interface StatusBadgeProps {
  type: 'health' | 'incident';
  status: HealthState | IncidentState | string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ type, status }) => {
  const norm = (status || '').toUpperCase();

  let badgeClass = 'badge-healthy';
  let label = norm;

  if (type === 'health') {
    switch (norm) {
      case 'HEALTHY':
        badgeClass = 'badge-healthy';
        break;
      case 'WARNING':
        badgeClass = 'badge-warning';
        break;
      case 'STALE':
        badgeClass = 'badge-stale';
        break;
      case 'RECOVERING':
        badgeClass = 'badge-recovering';
        break;
      case 'FAILED':
        badgeClass = 'badge-failed';
        break;
      default:
        badgeClass = 'badge-healthy';
    }
  } else {
    // Incident State
    switch (norm) {
      case 'DETECTED':
      case 'OPEN':
        badgeClass = 'badge-warning';
        break;
      case 'INVESTIGATING':
        badgeClass = 'badge-recovering';
        break;
      case 'RECOVERING':
        badgeClass = 'badge-recovering';
        break;
      case 'VERIFIED':
      case 'RESOLVED':
        badgeClass = 'badge-healthy';
        break;
      case 'FAILED':
        badgeClass = 'badge-failed';
        break;
      case 'ESCALATED':
        badgeClass = 'badge-escalated';
        break;
      default:
        badgeClass = 'badge-warning';
    }
  }

  return (
    <span className={`status-badge ${badgeClass}`}>
      <span className="status-badge-dot" />
      {label}
    </span>
  );
};
