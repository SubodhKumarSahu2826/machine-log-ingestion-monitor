import React from 'react';
import type { Incident, RecoveryAttempt, Integration } from '../types';
import { formatDateTime } from '../utils/formatters';

interface RecoveryProofProps {
  incident: Incident;
  successfulAttempt: RecoveryAttempt | undefined;
  integration: Integration | undefined;
}

export const RecoveryProof: React.FC<RecoveryProofProps> = ({
  incident,
  successfulAttempt,
  integration,
}) => {
  const isResolved = incident.state === 'RESOLVED';

  if (!isResolved || !successfulAttempt) {
    return null;
  }

  return (
    <div className="section-panel proof-panel">
      <div className="section-header">
        <div>
          <span className="section-title">Telemetry Verification Proof</span>
          <span className="section-subtitle">
            Closed-loop database verification confirmation
          </span>
        </div>
        <span className="tag-verified-pill">✓ VERIFIED BY TELEMETRY</span>
      </div>

      <div className="proof-statement-banner">
        <strong>CRITICAL VERIFICATION RULE SATISFIED:</strong>
        <p>
          Recovery was verified by actual new machine data ingested, validated, and persisted in
          PostgreSQL. The system never declares success from recovery dispatch alone.
        </p>
      </div>

      <div className="proof-grid">
        <div className="proof-card">
          <span className="proof-card-label">1. NEW TELEMETRY RECEIVED</span>
          <span className="proof-card-val text-success">✓ CONFIRMED</span>
          <span className="proof-card-sub font-mono">
            received_at &gt; {formatDateTime(successfulAttempt.attempted_at)}
          </span>
        </div>

        <div className="proof-card">
          <span className="proof-card-label">2. EVENT PERSISTED IN DB</span>
          <span className="proof-card-val text-success">✓ PERSISTED</span>
          <span className="proof-card-sub font-mono">
            Unique event_id confirmed in PostgreSQL
          </span>
        </div>

        <div className="proof-card">
          <span className="proof-card-label">3. LAST_SEEN_AT ADVANCED</span>
          <span className="proof-card-val text-success">✓ ADVANCED</span>
          <span className="proof-card-sub font-mono">
            {formatDateTime(integration?.last_seen_at)}
          </span>
        </div>

        <div className="proof-card">
          <span className="proof-card-label">4. STREAM HEALTH RESTORED</span>
          <span className="proof-card-val text-success">✓ HEALTHY</span>
          <span className="proof-card-sub font-mono">
            Incident #{incident.id} RESOLVED
          </span>
        </div>
      </div>
    </div>
  );
};
