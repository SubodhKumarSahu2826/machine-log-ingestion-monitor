import React from 'react';
import type { IncidentState, RecoveryAttempt } from '../types';
import { formatDateTime } from '../utils/formatters';

interface TimelineProps {
  currentState: IncidentState;
  createdAt?: string;
  resolvedAt?: string | null;
  attempts?: RecoveryAttempt[];
}

export const Timeline: React.FC<TimelineProps> = ({
  currentState,
  createdAt,
  resolvedAt,
  attempts = [],
}) => {
  const isFailureBranch = currentState === 'FAILED' || currentState === 'ESCALATED';

  const successSteps: IncidentState[] = [
    'DETECTED',
    'OPEN',
    'INVESTIGATING',
    'RECOVERING',
    'VERIFIED',
    'RESOLVED',
  ];

  const failureSteps: IncidentState[] = [
    'DETECTED',
    'OPEN',
    'RECOVERING',
    'FAILED',
    'ESCALATED',
  ];

  const steps = isFailureBranch ? failureSteps : successSteps;
  const currentIndex = steps.indexOf(currentState);

  const getStepTimestamp = (step: IncidentState): string | null => {
    if (step === 'DETECTED' || step === 'OPEN') {
      return createdAt ? formatDateTime(createdAt) : null;
    }
    if (step === 'RESOLVED') {
      return resolvedAt ? formatDateTime(resolvedAt) : null;
    }
    if (step === 'RECOVERING' && attempts.length > 0) {
      return formatDateTime(attempts[0].attempted_at);
    }
    if (step === 'FAILED' && attempts.length > 0) {
      const lastFailed = [...attempts].reverse().find((a) => a.status === 'FAILURE');
      return lastFailed?.completed_at ? formatDateTime(lastFailed.completed_at) : null;
    }
    if (step === 'VERIFIED' && attempts.length > 0) {
      const successful = attempts.find((a) => a.status === 'SUCCESS');
      return successful?.completed_at ? formatDateTime(successful.completed_at) : null;
    }
    return null;
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">
          <span>Incident Lifecycle Timeline</span>
          <span
            style={{
              fontSize: '0.75rem',
              color: isFailureBranch ? '#f43f5e' : '#34d399',
              fontWeight: 600,
            }}
          >
            {isFailureBranch ? 'Escalation Flow' : 'Resolution Flow'}
          </span>
        </div>
      </div>
      <div className="panel-body" style={{ padding: '1.5rem 1rem' }}>
        <div className="timeline-stepper">
          {steps.map((step, idx) => {
            const isCompleted = currentIndex > idx || (step === 'RESOLVED' && currentState === 'RESOLVED');
            const isActive = currentIndex === idx;
            const isFailed = step === 'FAILED' || (step === 'ESCALATED' && currentState === 'ESCALATED');
            const timestamp = getStepTimestamp(step);

            let nodeClass = '';
            if (isCompleted) nodeClass = 'completed';
            if (isActive) nodeClass = isFailed ? 'failed' : 'active';

            return (
              <React.Fragment key={step}>
                <div className="timeline-step">
                  <div className={`step-node ${nodeClass}`}>
                    {isCompleted ? '✓' : idx + 1}
                  </div>
                  <div
                    className={`step-label ${
                      isActive ? 'active' : isCompleted ? 'completed' : ''
                    }`}
                  >
                    {step}
                  </div>
                  {timestamp && (
                    <div
                      style={{
                        fontSize: '0.68rem',
                        color: 'var(--text-dim)',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {timestamp.split(' ')[1] || timestamp}
                    </div>
                  )}
                </div>
                {idx < steps.length - 1 && (
                  <div
                    className={`step-connector ${
                      currentIndex > idx ? 'completed' : ''
                    }`}
                  />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </div>
  );
};
