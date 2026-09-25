import React from 'react';
import type { Integration, Incident } from '../types';
import { StatusIndicator } from './StatusIndicator';
import { formatFreshness } from '../utils/formatters';

interface FactoryFlowProps {
  integrations: Integration[];
  activeIncidentsByIntegration: Map<number, Incident>;
  onSelectIntegration: (id: number) => void;
  onSelectIncident: (id: number) => void;
}

export const FactoryFlow: React.FC<FactoryFlowProps> = ({
  integrations,
  activeIncidentsByIntegration,
  onSelectIntegration,
  onSelectIncident,
}) => {
  return (
    <div className="section-panel">
      <div className="section-header">
        <div>
          <span className="section-title">Factory Telemetry Pipeline</span>
          <span className="section-subtitle">
            Physical Equipment → Field Connectors → Ingestion Gateway → Freshness Monitor
          </span>
        </div>
        <div className="pipeline-legend">
          <span className="legend-item">
            <span className="legend-dot healthy" /> Operational
          </span>
          <span className="legend-item">
            <span className="legend-dot warning" /> Warning
          </span>
          <span className="legend-item">
            <span className="legend-dot stale" /> Stale / Interrupted
          </span>
        </div>
      </div>

      <div className="stream-pipeline-list">
        {integrations.length === 0 ? (
          <div className="empty-state">No factory integrations registered in database.</div>
        ) : (
          integrations.map((intg) => {
            const incident = activeIncidentsByIntegration.get(intg.id);
            const freshness = formatFreshness(intg.last_seen_at);
            const isAlert = intg.health_state === 'STALE' || intg.health_state === 'FAILED';

            return (
              <div
                key={intg.id}
                className={`stream-pipeline-row ${isAlert ? 'row-alert' : ''}`}
              >
                {/* 1. Machine Source */}
                <div className="stream-node machine-node">
                  <span className="node-tag">MACHINE #{intg.machine_id}</span>
                  <span className="node-name">Station {intg.machine_id} Unit</span>
                </div>

                <div className="node-arrow" aria-hidden="true">→</div>

                {/* 2. Field Connector */}
                <div className="stream-node connector-node">
                  <span className="node-tag">{intg.type} ADAPTER</span>
                  <span className="node-name">{intg.name}</span>
                </div>

                <div className="node-arrow" aria-hidden="true">→</div>

                {/* 3. Ingestion Endpoint */}
                <div className="stream-node ingestion-node">
                  <span className="node-tag">INGESTION API</span>
                  <span className="node-name font-mono">POST /api/v1/events</span>
                </div>

                <div className="node-arrow" aria-hidden="true">→</div>

                {/* 4. Stream Telemetry Status */}
                <div className="stream-node telemetry-node">
                  <div className="telemetry-meta">
                    <span className="meta-label">LAST SEEN:</span>
                    <span className="meta-val font-mono">{freshness.text}</span>
                  </div>
                  <div className="telemetry-status">
                    <StatusIndicator type="health" status={intg.health_state} size="sm" />
                  </div>
                </div>

                {/* Action Button */}
                <div className="stream-action">
                  {incident ? (
                    <button
                      className="btn btn-alert btn-sm"
                      onClick={() => onSelectIncident(incident.id)}
                    >
                      Incident #{incident.id} →
                    </button>
                  ) : (
                    <button
                      className="btn btn-subtle btn-sm"
                      onClick={() => onSelectIntegration(intg.id)}
                    >
                      Inspect Stream
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
