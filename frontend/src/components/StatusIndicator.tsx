import React from 'react';
import type { HealthState, IncidentState } from '../types';

interface StatusIndicatorProps {
  type?: 'health' | 'incident';
  status: HealthState | IncidentState | string;
  size?: 'sm' | 'md';
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  type = 'health',
  status,
  size = 'md',
}) => {
  const norm = (status || '').toUpperCase();

  let stateClass = 'status-healthy';
  let symbol = '●';
  let label = norm;

  if (type === 'health') {
    switch (norm) {
      case 'HEALTHY':
        stateClass = 'status-healthy';
        symbol = '●';
        break;
      case 'WARNING':
        stateClass = 'status-warning';
        symbol = '▲';
        break;
      case 'STALE':
        stateClass = 'status-stale';
        symbol = '■';
        break;
      case 'RECOVERING':
        stateClass = 'status-recovering';
        symbol = '⟳';
        break;
      case 'FAILED':
        stateClass = 'status-failed';
        symbol = '✕';
        break;
    }
  } else {
    // Incident State
    switch (norm) {
      case 'DETECTED':
      case 'OPEN':
        stateClass = 'status-warning';
        symbol = '▲';
        break;
      case 'INVESTIGATING':
      case 'RECOVERING':
        stateClass = 'status-recovering';
        symbol = '⟳';
        break;
      case 'VERIFIED':
      case 'RESOLVED':
        stateClass = 'status-healthy';
        symbol = '✓';
        break;
      case 'FAILED':
        stateClass = 'status-failed';
        symbol = '✕';
        break;
      case 'ESCALATED':
        stateClass = 'status-escalated';
        symbol = '⚠';
        break;
    }
  }

  return (
    <span className={`status-indicator ${stateClass} ${size === 'sm' ? 'status-sm' : ''}`}>
      <span className="status-symbol" aria-hidden="true">
        {symbol}
      </span>
      <span className="status-label">{label}</span>
    </span>
  );
};
