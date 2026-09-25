import React, { useState, useMemo } from 'react';
import type { Integration, Incident } from '../types';
import { IntegrationTable } from '../components/IntegrationTable';

interface IntegrationsPageProps {
  integrations: Integration[];
  incidents: Incident[];
  selectedIntegrationId?: number | null;
  onSelectIntegration: (id: number) => void;
  onSelectIncident: (id: number) => void;
  onRefresh: () => void;
  isLoading: boolean;
}

export const IntegrationsPage: React.FC<IntegrationsPageProps> = ({
  integrations,
  incidents,
  selectedIntegrationId,
  onSelectIntegration,
  onSelectIncident,
  onRefresh,
  isLoading,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [healthFilter, setHealthFilter] = useState('ALL');

  const activeIncidentsByIntegration = useMemo(() => {
    const map = new Map<number, Incident>();
    incidents.forEach((inc) => {
      if (inc.state !== 'RESOLVED') {
        map.set(inc.integration_id, inc);
      }
    });
    return map;
  }, [incidents]);

  const filteredIntegrations = useMemo(() => {
    return integrations.filter((intg) => {
      const matchFilter = healthFilter === 'ALL' || intg.health_state === healthFilter;
      const matchSearch =
        intg.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        String(intg.machine_id).includes(searchTerm);
      return matchFilter && matchSearch;
    });
  }, [integrations, healthFilter, searchTerm]);

  return (
    <div className="integrations-page">
      <div className="section-panel">
        <div className="section-header">
          <div>
            <span className="section-title">Factory Equipment Integrations Registry</span>
            <span className="section-subtitle">
              Configured machine lines, protocol adapters & freshness monitoring limits
            </span>
          </div>

          <div className="filter-controls">
            <input
              type="text"
              className="tech-input"
              placeholder="Search integration or machine..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{ width: '220px' }}
            />
            <select
              className="tech-select"
              value={healthFilter}
              onChange={(e) => setHealthFilter(e.target.value)}
              style={{ width: '140px' }}
            >
              <option value="ALL">All States</option>
              <option value="HEALTHY">HEALTHY</option>
              <option value="WARNING">WARNING</option>
              <option value="STALE">STALE</option>
              <option value="RECOVERING">RECOVERING</option>
              <option value="FAILED">FAILED</option>
            </select>
            <button className="btn btn-secondary btn-sm" onClick={onRefresh} disabled={isLoading}>
              {isLoading ? 'Syncing...' : '↻ Refresh'}
            </button>
          </div>
        </div>

        <IntegrationTable
          integrations={filteredIntegrations}
          activeIncidentsByIntegration={activeIncidentsByIntegration}
          selectedIntegrationId={selectedIntegrationId}
          onSelectIntegration={onSelectIntegration}
          onSelectIncident={onSelectIncident}
        />
      </div>
    </div>
  );
};
