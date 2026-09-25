import React from 'react';
import type { Integration, Incident } from '../types';
import { FactoryFlow } from '../components/FactoryFlow';
import { formatDateTime } from '../utils/formatters';

interface OperationsPageProps {
  integrations: Integration[];
  incidents: Incident[];
  onSelectIntegration: (id: number) => void;
  onSelectIncident: (id: number) => void;
  onNavigateToSimulator: () => void;
}

export const OperationsPage: React.FC<OperationsPageProps> = ({
  integrations,
  incidents,
  onSelectIntegration,
  onSelectIncident,
  onNavigateToSimulator,
}) => {
  // Map active incidents to their integrations
  const activeIncidentsByIntegration = new Map<number, Incident>();
  incidents.forEach((inc) => {
    if (inc.state !== 'RESOLVED') {
      activeIncidentsByIntegration.set(inc.integration_id, inc);
    }
  });

  const staleOrFailedIntegrations = integrations.filter(
    (i) => i.health_state === 'STALE' || i.health_state === 'FAILED'
  );

  const isCalm = staleOrFailedIntegrations.length === 0;

  return (
    <div className="operations-page">
      {/* Calm vs Attention Operational Banner */}
      {isCalm ? (
        <div className="calm-status-banner">
          <div className="calm-indicator-icon">✓</div>
          <div>
            <div className="calm-title">ALL FACTORY DATA STREAMS OPERATIONAL</div>
            <div className="calm-subtitle">
              {integrations.length} equipment streams delivering telemetry within expected thresholds. Zero open incidents.
            </div>
          </div>
        </div>
      ) : (
        <div className="attention-required-container">
          {staleOrFailedIntegrations.map((intg) => {
            const inc = activeIncidentsByIntegration.get(intg.id);

            return (
              <div key={intg.id} className="attention-banner">
                <div className="attention-badge">ATTENTION REQUIRED</div>
                <div className="attention-details">
                  <div className="attention-machine">
                    <strong>{intg.name}</strong> (Machine #{intg.machine_id})
                  </div>
                  <div className="attention-reason">
                    Telemetry data stream stopped arriving. Stream is <strong>{intg.health_state}</strong>.
                  </div>
                  <div className="attention-meta font-mono">
                    Last Seen: {formatDateTime(intg.last_seen_at)} • Expected every {intg.expected_interval_seconds || 30}s
                  </div>
                </div>
                <div className="attention-actions">
                  {inc ? (
                    <button
                      className="btn btn-alert"
                      onClick={() => onSelectIncident(inc.id)}
                    >
                      VIEW INCIDENT #{inc.id} →
                    </button>
                  ) : (
                    <button
                      className="btn btn-secondary"
                      onClick={() => onSelectIntegration(intg.id)}
                    >
                      INSPECT STREAM →
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Factory Pipeline Flow */}
      <FactoryFlow
        integrations={integrations}
        activeIncidentsByIntegration={activeIncidentsByIntegration}
        onSelectIntegration={onSelectIntegration}
        onSelectIncident={onSelectIncident}
      />

      {/* Stream Summary Strip */}
      <div className="pipeline-summary-strip">
        <div className="summary-item">
          <span className="summary-label">TOTAL INTEGRATIONS</span>
          <span className="summary-val font-mono">{integrations.length}</span>
        </div>
        <div className="summary-item">
          <span className="summary-label">HEALTHY</span>
          <span className="summary-val font-mono text-success">
            {integrations.filter((i) => i.health_state === 'HEALTHY').length}
          </span>
        </div>
        <div className="summary-item">
          <span className="summary-label">WARNING / AT RISK</span>
          <span className="summary-val font-mono text-warning">
            {integrations.filter((i) => i.health_state === 'WARNING').length}
          </span>
        </div>
        <div className="summary-item">
          <span className="summary-label">STALE / FAILED</span>
          <span className="summary-val font-mono text-danger">
            {staleOrFailedIntegrations.length}
          </span>
        </div>
        <div className="summary-item">
          <span className="summary-label">ACTIVE INCIDENTS</span>
          <span className="summary-val font-mono text-purple">
            {incidents.filter((i) => i.state !== 'RESOLVED').length}
          </span>
        </div>
        <div className="summary-actions">
          <button className="btn btn-subtle btn-xs" onClick={onNavigateToSimulator}>
            Simulator / Judge Mode →
          </button>
        </div>
      </div>
    </div>
  );
};
