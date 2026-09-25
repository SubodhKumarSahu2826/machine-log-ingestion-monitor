import React, { useState } from 'react';
import type { RecoveryAction } from '../types';

interface RecoveryActionDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (action: RecoveryAction) => void;
  isSubmitting: boolean;
  incidentId: number;
}

const ACTION_DESCRIPTIONS: Record<RecoveryAction, { title: string; desc: string }> = {
  RETRY_CONNECTION: {
    title: 'Retry Connection',
    desc: 'Simulates re-establishing transient TCP/IP connection or protocol handshake with the machine.',
  },
  RECONNECT_CONNECTOR: {
    title: 'Reconnect Connector',
    desc: 'Simulates restarting the local field connector daemon and re-registering stream hooks.',
  },
  REPLAY_EVENTS: {
    title: 'Replay Events',
    desc: 'Requests the connector to replay missing machine event cycles from local disk buffer.',
  },
};

export const RecoveryActionDialog: React.FC<RecoveryActionDialogProps> = ({
  isOpen,
  onClose,
  onConfirm,
  isSubmitting,
  incidentId,
}) => {
  const [selectedAction, setSelectedAction] = useState<RecoveryAction>('RETRY_CONNECTION');

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="panel-title">
            <span>Execute Controlled Recovery</span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginLeft: '0.5rem' }}>
              (Incident #{incidentId})
            </span>
          </div>
          <button
            onClick={onClose}
            disabled={isSubmitting}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-muted)',
              fontSize: '1.25rem',
              cursor: 'pointer',
            }}
          >
            ×
          </button>
        </div>

        <div className="modal-body">
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
            Select a controlled recovery action. The recovery process moves the incident to{' '}
            <strong style={{ color: '#38bdf8' }}>RECOVERING</strong> and will only resolve upon
            confirming actual new machine data in PostgreSQL.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {(Object.keys(ACTION_DESCRIPTIONS) as RecoveryAction[]).map((action) => {
              const info = ACTION_DESCRIPTIONS[action];
              const isSelected = selectedAction === action;

              return (
                <div
                  key={action}
                  onClick={() => !isSubmitting && setSelectedAction(action)}
                  style={{
                    background: isSelected ? 'rgba(6, 182, 212, 0.12)' : 'rgba(30, 41, 59, 0.4)',
                    border: `1px solid ${isSelected ? 'rgba(6, 182, 212, 0.5)' : 'var(--border-subtle)'}`,
                    borderRadius: '8px',
                    padding: '0.85rem 1rem',
                    cursor: isSubmitting ? 'not-allowed' : 'pointer',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '0.75rem',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <input
                    type="radio"
                    name="recovery-action"
                    checked={isSelected}
                    onChange={() => setSelectedAction(action)}
                    disabled={isSubmitting}
                    style={{ marginTop: '3px' }}
                  />
                  <div>
                    <div
                      style={{
                        fontWeight: 600,
                        fontSize: '0.88rem',
                        color: isSelected ? '#38bdf8' : '#f8fafc',
                        marginBottom: '0.2rem',
                      }}
                    >
                      {action} ({info.title})
                    </div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                      {info.desc}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="modal-footer">
          <button
            className="btn btn-secondary"
            onClick={onClose}
            disabled={isSubmitting}
          >
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={() => onConfirm(selectedAction)}
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <>
                <span className="spinner" /> Initiating Recovery...
              </>
            ) : (
              'Initiate Recovery'
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
