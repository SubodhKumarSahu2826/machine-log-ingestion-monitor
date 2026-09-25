import React from 'react';
import type { Integration, Incident } from '../types';
import { StatusIndicator } from './StatusIndicator';
import { formatDateTime, formatFreshness } from '../utils/formatters';

interface IntegrationTableProps {
  integrations: Integration[];
  activeIncidentsByIntegration: Map<number, Incident>;
  selectedIntegrationId?: number | null;
  onSelectIntegration: (id: number) => void;
  onSelectIncident: (id: number) => void;
}

export const IntegrationTable: React.FC<IntegrationTableProps> = ({
  integrations,
  activeIncidentsByIntegration,
  selectedIntegrationId,
  onSelectIntegration,
  onSelectIncident,
}) => {
  return (
    <div className="table-responsive">
      <table className="tech-table">
        <thead>
          <tr>
            <th>Integration</th>
            <th>Machine ID</th>
            <th>Protocol</th>
            <th>Expected</th>
            <th>Stale Limit</th>
            <th>Last Telemetry</th>
            <th>Health</th>
            <th>Incident</th>
            <th style={{ textAlign: 'right' }}>Actions</th>
          </tr>
        </thead>
        <tbody>
          {integrations.length === 0 ? (
            <tr>
              <td colSpan={9} className="table-empty">
                No integrations registered.
              </td>
            </tr>
          ) : (
            integrations.map((intg) => {
              const freshness = formatFreshness(intg.last_seen_at);
              const incident = activeIncidentsByIntegration.get(intg.id);

              const isSelected = selectedIntegrationId === intg.id;
              return (
                <tr
                  key={intg.id}
                  className={`${intg.health_state === 'STALE' ? 'row-stale' : ''} ${isSelected ? 'row-selected' : ''}`}
                >
                  <td>
                    <span
                      className="link-title"
                      onClick={() => onSelectIntegration(intg.id)}
                    >
                      {intg.name}
                    </span>
                    <span className="sub-id font-mono">ID: {intg.id}</span>
                  </td>
                  <td className="font-mono">#{intg.machine_id}</td>
                  <td>
                    <span className="code-pill">{intg.type}</span>
                  </td>
                  <td className="font-mono text-muted">{intg.expected_interval_seconds || 30}s</td>
                  <td className="font-mono text-muted">{intg.stale_threshold_seconds || 120}s</td>
                  <td>
                    <div className="font-mono text-bold">{freshness.text}</div>
                    <div className="font-mono text-xs text-muted">
                      {formatDateTime(intg.last_seen_at)}
                    </div>
                  </td>
                  <td>
                    <StatusIndicator type="health" status={intg.health_state} size="sm" />
                  </td>
                  <td>
                    {incident ? (
                      <button
                        className="btn btn-alert btn-xs"
                        onClick={() => onSelectIncident(incident.id)}
                      >
                        <StatusIndicator type="incident" status={incident.state} size="sm" />
                        <span className="font-mono ml-1">#{incident.id}</span>
                      </button>
                    ) : (
                      <span className="text-muted font-mono">—</span>
                    )}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <button
                      className="btn btn-subtle btn-xs"
                      onClick={() => onSelectIntegration(intg.id)}
                    >
                      Inspect
                    </button>
                  </td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
};
