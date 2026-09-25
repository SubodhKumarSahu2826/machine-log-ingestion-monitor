import React from 'react';
import type { DiagnosticResult } from '../types';
import { getCheckStatusStyle } from '../utils/formatters';

interface DiagnosisPanelProps {
  diagnostic: DiagnosticResult | null;
  onRunDiagnostics: () => void;
  isRunning: boolean;
  isResolved: boolean;
}

interface CheckMetadata {
  key: keyof DiagnosticResult['checks'];
  label: string;
  scope: string;
}

const CHECK_KEYS: CheckMetadata[] = [
  { key: 'machine_heartbeat', label: 'Machine Heartbeat', scope: 'Controller availability & heartbeat packet freshness' },
  { key: 'network', label: 'Network Connectivity', scope: 'TCP socket link, route ping & transport latency' },
  { key: 'connector', label: 'Connector Daemon', scope: 'Adapter process execution & streaming loop health' },
  { key: 'authentication', label: 'Authentication', scope: 'API token integrity, certificate & handshake verification' },
  { key: 'parser', label: 'Payload Parser', scope: 'Telemetry JSON payload schema validation & type parsing' },
  { key: 'ingestion', label: 'Ingestion Pipeline', scope: 'Database persistence queue responsiveness & backend write' },
];

export const DiagnosisPanel: React.FC<DiagnosisPanelProps> = ({
  diagnostic,
  onRunDiagnostics,
  isRunning,
  isResolved,
}) => {
  return (
    <div className="section-panel">
      <div className="section-header">
        <div>
          <span className="section-title">Deterministic Root-Cause Diagnostics</span>
          <span className="section-subtitle">
            Automated verification across 6 telemetry failure domains
          </span>
        </div>
        <div>
          <button
            className="btn btn-secondary btn-sm"
            onClick={onRunDiagnostics}
            disabled={isRunning || isResolved}
          >
            {isRunning ? 'Probing Vectors...' : 'Execute Diagnostics'}
          </button>
        </div>
      </div>

      {diagnostic && (
        <div className="probable-cause-banner">
          <div className="cause-header">
            <span className="cause-tag">DETERMINED PROBABLE CAUSE</span>
            <span className="cause-title font-mono">{diagnostic.probable_cause}</span>
          </div>
          <div className="cause-desc">{diagnostic.explanation}</div>
        </div>
      )}

      <div className="checks-grid">
        {CHECK_KEYS.map(({ key, label, scope }) => {
          const check = diagnostic?.checks?.[key];
          const status = check?.status || 'UNKNOWN';
          const style = getCheckStatusStyle(status);

          return (
            <div key={key} className={`check-card ${style.className}`}>
              <div className="check-card-header">
                <span className="check-title">{label}</span>
                <span className={`check-tag ${style.className}`}>
                  <span className="check-symbol" aria-hidden="true">{style.symbol}</span>
                  {status}
                </span>
              </div>
              <div className="check-detail font-mono">
                {check?.details || scope}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
