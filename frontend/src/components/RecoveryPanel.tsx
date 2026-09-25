import React, { useState } from 'react';
import type { Incident, RecoveryAttempt, RecoveryAction } from '../types';
import { formatDateTime } from '../utils/formatters';

interface RecoveryPanelProps {
  incident: Incident;
  attempts: RecoveryAttempt[];
  onInitiateRecovery: (action: RecoveryAction) => void;
  onVerifyRecovery: () => void;
  isRecovering: boolean;
  isVerifying: boolean;
}

const ACTION_DESCRIPTIONS: Record<RecoveryAction, { title: string; desc: string }> = {
  RETRY_CONNECTION: {
    title: 'Retry Connection',
    desc: 'Re-establishes transient network transport and protocol socket handshake with equipment.',
  },
  RECONNECT_CONNECTOR: {
    title: 'Reconnect Connector',
    desc: 'Restarts field adapter service and resets local memory stream buffer.',
  },
  REPLAY_EVENTS: {
    title: 'Replay Events',
    desc: 'Requests connector to replay backlog machine cycles from persistent disk spool.',
  },
};

export const RecoveryPanel: React.FC<RecoveryPanelProps> = ({
  incident,
  attempts,
  onInitiateRecovery,
  onVerifyRecovery,
  isRecovering,
  isVerifying,
}) => {
  const [selectedAction, setSelectedAction] = useState<RecoveryAction>('RETRY_CONNECTION');

  const isResolved = incident.state === 'RESOLVED';
  const isEscalated = incident.state === 'ESCALATED';
  const isCurrentlyRecovering = incident.state === 'RECOVERING';

  const failedAttemptsCount = attempts.filter((a) => a.status === 'FAILURE').length;
  const maxAttempts = 3;

  return (
    <div className="section-panel">
      <div className="section-header">
        <div>
          <span className="section-title">Closed-Loop Autonomous Recovery</span>
          <span className="section-subtitle">
            Controlled action dispatch & bounded retry execution
          </span>
        </div>
        <div className="retry-counter-box">
          <span className="retry-label">BOUNDED RETRIES:</span>
          <span
            className={`retry-value font-mono ${
              isEscalated ? 'text-danger' : failedAttemptsCount > 0 ? 'text-warning' : 'text-primary'
            }`}
          >
            {Math.min(failedAttemptsCount, maxAttempts)} / {maxAttempts}
          </span>
          {isEscalated && <span className="tag-escalated">ATTEMPTS EXHAUSTED</span>}
        </div>
      </div>

      {/* Escalation Alert if max attempts exceeded */}
      {isEscalated && (
        <div className="escalation-alert">
          <div className="alert-heading">CRITICAL: RECOVERY ATTEMPTS EXHAUSTED (3/3 FAILED)</div>
          <div className="alert-body">
            Maximum automated recovery attempts exceeded without telemetry recovery. Stream is
            marked <strong>FAILED</strong> and incident is escalated for physical maintenance.
          </div>
        </div>
      )}

      {/* Recovery Controls (if not resolved and not escalated) */}
      {!isResolved && !isEscalated && (
        <div className="recovery-control-box">
          <div className="action-options-grid">
            {(Object.keys(ACTION_DESCRIPTIONS) as RecoveryAction[]).map((act) => {
              const info = ACTION_DESCRIPTIONS[act];
              const isSelected = selectedAction === act;

              return (
                <label
                  key={act}
                  className={`action-option-card ${isSelected ? 'selected' : ''}`}
                >
                  <input
                    type="radio"
                    name="recovery_action"
                    checked={isSelected}
                    onChange={() => setSelectedAction(act)}
                    disabled={isCurrentlyRecovering || isRecovering}
                  />
                  <div className="option-content">
                    <span className="option-title font-mono">{act}</span>
                    <span className="option-desc">{info.desc}</span>
                  </div>
                </label>
              );
            })}
          </div>

          <div className="action-buttons-row">
            <button
              className="btn btn-primary"
              onClick={() => onInitiateRecovery(selectedAction)}
              disabled={isCurrentlyRecovering || isRecovering}
            >
              {isRecovering ? 'Dispatching Action...' : `Initiate ${selectedAction}`}
            </button>

            <button
              className="btn btn-success"
              onClick={onVerifyRecovery}
              disabled={!isCurrentlyRecovering || isVerifying}
              title={
                !isCurrentlyRecovering
                  ? 'Verification is active when incident is in RECOVERING state'
                  : 'Verify new telemetry arrival in PostgreSQL'
              }
            >
              {isVerifying ? 'Checking Telemetry...' : 'Verify Telemetry Arrival'}
            </button>
          </div>
        </div>
      )}

      {/* Recovery Attempt History */}
      <div className="table-responsive mt-3">
        <table className="tech-table">
          <thead>
            <tr>
              <th style={{ width: '60px' }}>Attempt</th>
              <th>Action</th>
              <th>Status</th>
              <th>Started At</th>
              <th>Completed At</th>
              <th>Outcome / Telemetry Proof</th>
            </tr>
          </thead>
          <tbody>
            {attempts.length === 0 ? (
              <tr>
                <td colSpan={6} className="table-empty">
                  No recovery attempts dispatched yet.
                </td>
              </tr>
            ) : (
              attempts.map((attempt, index) => {
                let badgeClass = 'tag-unknown';
                if (attempt.status === 'SUCCESS') badgeClass = 'tag-pass';
                if (attempt.status === 'FAILURE') badgeClass = 'tag-fail';
                if (attempt.status === 'STARTED') badgeClass = 'tag-recovering';

                return (
                  <tr key={attempt.id}>
                    <td className="font-mono text-bold">#{index + 1}</td>
                    <td className="font-mono">{attempt.action}</td>
                    <td>
                      <span className={`tag-status ${badgeClass}`}>
                        {attempt.status}
                      </span>
                    </td>
                    <td className="font-mono text-xs text-muted">
                      {formatDateTime(attempt.attempted_at)}
                    </td>
                    <td className="font-mono text-xs text-muted">
                      {formatDateTime(attempt.completed_at)}
                    </td>
                    <td className="text-muted text-xs">
                      {attempt.result_message || 'In progress...'}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
