import React from 'react';
import type { RecoveryAttempt } from '../types';
import { formatDateTime } from '../utils/formatters';

interface RecoveryAttemptsProps {
  attempts: RecoveryAttempt[];
}

export const RecoveryAttempts: React.FC<RecoveryAttemptsProps> = ({ attempts }) => {
  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">
          <span>Recovery Attempt History</span>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
            ({attempts.length} {attempts.length === 1 ? 'attempt' : 'attempts'} recorded)
          </span>
        </div>
      </div>
      <div className="panel-body" style={{ padding: 0 }}>
        {attempts.length === 0 ? (
          <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            No recovery attempts initiated yet.
          </div>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ width: '60px' }}>#</th>
                  <th>Action</th>
                  <th>Status</th>
                  <th>Started At</th>
                  <th>Completed At</th>
                  <th>Result / Telemetry Details</th>
                </tr>
              </thead>
              <tbody>
                {attempts.map((attempt, index) => {
                  let statusColor = '#94a3b8';
                  if (attempt.status === 'SUCCESS') statusColor = '#34d399';
                  if (attempt.status === 'FAILURE') statusColor = '#f87171';
                  if (attempt.status === 'STARTED') statusColor = '#38bdf8';

                  return (
                    <tr key={attempt.id}>
                      <td style={{ fontWeight: 600, color: 'var(--text-dim)' }}>
                        #{index + 1}
                      </td>
                      <td style={{ fontWeight: 600 }}>{attempt.action}</td>
                      <td>
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.35rem',
                            fontWeight: 700,
                            fontSize: '0.75rem',
                            color: statusColor,
                          }}
                        >
                          <span
                            style={{
                              width: '6px',
                              height: '6px',
                              borderRadius: '50%',
                              backgroundColor: statusColor,
                            }}
                          />
                          {attempt.status}
                        </span>
                      </td>
                      <td>{formatDateTime(attempt.attempted_at)}</td>
                      <td>{formatDateTime(attempt.completed_at)}</td>
                      <td style={{ maxWidth: '300px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                        {attempt.result_message || '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
