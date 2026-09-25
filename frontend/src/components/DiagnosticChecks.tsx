import React from 'react';
import type { DiagnosticResult, CheckStatus } from '../types';
import { getCheckStatusStyle } from '../utils/formatters';

interface DiagnosticChecksProps {
  diagnostic: DiagnosticResult | null;
  onRunDiagnostics?: () => void;
  isRunning?: boolean;
}

interface CheckConfig {
  key: keyof DiagnosticResult['checks'];
  name: string;
  description: string;
}

const CHECK_CONFIGS: CheckConfig[] = [
  {
    key: 'machine_heartbeat',
    name: 'Machine Heartbeat',
    description: 'Verifies physical controller ping and heartbeat stream',
  },
  {
    key: 'network',
    name: 'Network Connectivity',
    description: 'Probes network socket and interface latency',
  },
  {
    key: 'connector',
    name: 'Connector Health',
    description: 'Checks field adapter process and buffer health',
  },
  {
    key: 'authentication',
    name: 'Authentication & Credentials',
    description: 'Validates API keys, mutual TLS certificates, and tokens',
  },
  {
    key: 'parser',
    name: 'Payload Parser',
    description: 'Checks schema adherence and payload syntax parsing',
  },
  {
    key: 'ingestion',
    name: 'Ingestion Pipeline',
    description: 'Checks database responsiveness and broker queue health',
  },
];

export const DiagnosticChecks: React.FC<DiagnosticChecksProps> = ({
  diagnostic,
  onRunDiagnostics,
  isRunning,
}) => {
  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">
          <span>Deterministic Diagnostic Engine</span>
          {diagnostic && (
            <span
              style={{
                fontSize: '0.75rem',
                fontWeight: 500,
                color: 'var(--text-dim)',
                marginLeft: '0.5rem',
              }}
            >
              (Evaluated: {new Date(diagnostic.evaluated_at).toLocaleTimeString()})
            </span>
          )}
        </div>
        {onRunDiagnostics && (
          <button
            className="btn btn-secondary btn-sm"
            onClick={onRunDiagnostics}
            disabled={isRunning}
          >
            {isRunning ? (
              <>
                <span className="spinner" /> Running Diagnostics...
              </>
            ) : (
              'Run Diagnostics'
            )}
          </button>
        )}
      </div>

      <div className="panel-body">
        {diagnostic && (
          <div
            style={{
              background: 'rgba(30, 41, 59, 0.4)',
              border: '1px solid var(--border-subtle)',
              borderRadius: '6px',
              padding: '0.85rem 1rem',
              marginBottom: '1rem',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.3rem' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-muted)' }}>
                PROBABLE CAUSE:
              </span>
              <span
                style={{
                  fontSize: '0.85rem',
                  fontWeight: 700,
                  color: diagnostic.probable_cause === 'MACHINE_OFFLINE' ? '#f43f5e' : '#38bdf8',
                  letterSpacing: '0.03em',
                }}
              >
                {diagnostic.probable_cause}
              </span>
            </div>
            <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              {diagnostic.explanation}
            </div>
          </div>
        )}

        <div className="checks-grid">
          {CHECK_CONFIGS.map(({ key, name, description }) => {
            const checkData = diagnostic?.checks?.[key];
            const status: CheckStatus = checkData?.status || 'UNKNOWN';
            const style = getCheckStatusStyle(status);

            return (
              <div key={key} className="check-item">
                <div className="check-header">
                  <span className="check-name">{name}</span>
                  <span
                    className="check-status-tag"
                    style={{
                      background: style.bg,
                      color: style.text,
                      border: style.border,
                    }}
                  >
                    {status}
                  </span>
                </div>
                <div className="check-details">
                  {checkData?.details || description}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
