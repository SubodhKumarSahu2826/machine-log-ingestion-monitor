import React, { useState, useMemo } from 'react';
import type { Integration, Incident } from '../types';
import { StatusBadge } from '../components/StatusBadge';
import { MetricCard } from '../components/MetricCard';
import { formatDateTime, formatFreshness } from '../utils/formatters';

interface DashboardPageProps {
  integrations: Integration[];
  incidents: Incident[];
  onSelectIntegration: (id: number) => void;
  onSelectIncident: (id: number) => void;
  onRefresh: () => void;
  isLoading: boolean;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  integrations,
  incidents,
  onSelectIntegration,
  onSelectIncident,
  onRefresh,
  isLoading,
}) => {
  const [filterState, setFilterState] = useState<string>('ALL');
  const [searchTerm, setSearchTerm] = useState<string>('');

  // Active incidents map: integration_id -> incident
  const activeIncidentsByIntegration = useMemo(() => {
    const map = new Map<number, Incident>();
    incidents.forEach((inc) => {
      if (inc.state !== 'RESOLVED') {
        map.set(inc.integration_id, inc);
      }
    });
    return map;
  }, [incidents]);

  // Metric counts
  const counts = useMemo(() => {
    let healthy = 0;
    let warning = 0;
    let stale = 0;
    let recovering = 0;
    let failed = 0;

    integrations.forEach((intg) => {
      switch (intg.health_state) {
        case 'HEALTHY':
          healthy++;
          break;
        case 'WARNING':
          warning++;
          break;
        case 'STALE':
          stale++;
          break;
        case 'RECOVERING':
          recovering++;
          break;
        case 'FAILED':
          failed++;
          break;
      }
    });

    const openIncidents = incidents.filter((i) => i.state !== 'RESOLVED').length;

    return {
      total: integrations.length,
      healthy,
      warning,
      stale,
      recovering,
      failed,
      openIncidents,
    };
  }, [integrations, incidents]);

  // Filtered integrations
  const filteredIntegrations = useMemo(() => {
    return integrations.filter((intg) => {
      const matchesFilter =
        filterState === 'ALL' || intg.health_state === filterState;
      const matchesSearch =
        intg.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        String(intg.machine_id).includes(searchTerm);
      return matchesFilter && matchesSearch;
    });
  }, [integrations, filterState, searchTerm]);

  return (
    <div>
      {/* Metric Cards Row */}
      <div className="metrics-grid">
        <MetricCard
          title="Total Integrations"
          value={counts.total}
          subtitle="Monitored stream endpoints"
        />
        <MetricCard
          title="Healthy"
          value={counts.healthy}
          valueColor="#10b981"
          subtitle="Within interval threshold"
        />
        <MetricCard
          title="Warning"
          value={counts.warning}
          valueColor="#f59e0b"
          subtitle="Approaching stale threshold"
        />
        <MetricCard
          title="Stale"
          value={counts.stale}
          valueColor="#f43f5e"
          subtitle="Telemetry interrupted"
        />
        <MetricCard
          title="Recovering"
          value={counts.recovering}
          valueColor="#06b6d4"
          subtitle="Recovery action in progress"
        />
        <MetricCard
          title="Failed"
          value={counts.failed}
          valueColor="#ef4444"
          subtitle="Escalated / failed retries"
        />
        <MetricCard
          title="Open Incidents"
          value={counts.openIncidents}
          valueColor="#a855f7"
          subtitle="Requiring attention"
        />
      </div>

      {/* Main Panel: Integrations Table */}
      <div className="panel">
        <div className="panel-header">
          <div className="panel-title">
            <span>Machine Data Streams & Telemetry Status</span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
              ({filteredIntegrations.length} displayed)
            </span>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            <input
              type="text"
              placeholder="Search integration or machine..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="form-input"
              style={{ width: '220px', padding: '0.35rem 0.65rem', fontSize: '0.8rem' }}
            />
            <select
              value={filterState}
              onChange={(e) => setFilterState(e.target.value)}
              className="form-select"
              style={{ width: '150px', padding: '0.35rem 0.65rem', fontSize: '0.8rem' }}
            >
              <option value="ALL">All States</option>
              <option value="HEALTHY">HEALTHY</option>
              <option value="WARNING">WARNING</option>
              <option value="STALE">STALE</option>
              <option value="RECOVERING">RECOVERING</option>
              <option value="FAILED">FAILED</option>
            </select>
            <button
              className="btn btn-secondary btn-sm"
              onClick={onRefresh}
              disabled={isLoading}
            >
              {isLoading ? <span className="spinner" /> : '↻ Refresh'}
            </button>
          </div>
        </div>

        <div className="panel-body" style={{ padding: 0 }}>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Integration</th>
                  <th>Machine ID</th>
                  <th>Type</th>
                  <th>Health State</th>
                  <th>Freshness</th>
                  <th>Last Seen</th>
                  <th>Active Incident</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredIntegrations.length === 0 ? (
                  <tr>
                    <td colSpan={8} style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                      No integrations match the current criteria.
                    </td>
                  </tr>
                ) : (
                  filteredIntegrations.map((intg) => {
                    const freshness = formatFreshness(intg.last_seen_at);
                    const activeIncident = activeIncidentsByIntegration.get(intg.id);

                    let freshnessColor = '#10b981';
                    if (freshness.status === 'warning') freshnessColor = '#f59e0b';
                    if (freshness.status === 'stale') freshnessColor = '#f43f5e';
                    if (freshness.status === 'none') freshnessColor = '#64748b';

                    return (
                      <tr key={intg.id}>
                        <td style={{ fontWeight: 600, color: '#f8fafc' }}>
                          <span
                            onClick={() => onSelectIntegration(intg.id)}
                            style={{ cursor: 'pointer', textDecoration: 'underline', textUnderlineOffset: '3px' }}
                          >
                            {intg.name}
                          </span>
                        </td>
                        <td style={{ color: 'var(--text-muted)' }}>Machine #{intg.machine_id}</td>
                        <td>
                          <span
                            style={{
                              background: 'rgba(51, 65, 85, 0.4)',
                              padding: '0.15rem 0.45rem',
                              borderRadius: '4px',
                              fontSize: '0.75rem',
                              color: 'var(--text-muted)',
                            }}
                          >
                            {intg.type}
                          </span>
                        </td>
                        <td>
                          <StatusBadge type="health" status={intg.health_state} />
                        </td>
                        <td style={{ color: freshnessColor, fontWeight: 600, fontSize: '0.82rem' }}>
                          {freshness.text}
                        </td>
                        <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                          {formatDateTime(intg.last_seen_at)}
                        </td>
                        <td>
                          {activeIncident ? (
                            <button
                              className="btn btn-secondary btn-sm"
                              onClick={() => onSelectIncident(activeIncident.id)}
                              style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}
                            >
                              <StatusBadge type="incident" status={activeIncident.state} />
                              <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                                #{activeIncident.id}
                              </span>
                            </button>
                          ) : (
                            <span style={{ color: 'var(--text-dim)', fontSize: '0.8rem' }}>—</span>
                          )}
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <div style={{ display: 'inline-flex', gap: '0.4rem' }}>
                            <button
                              className="btn btn-secondary btn-sm"
                              onClick={() => onSelectIntegration(intg.id)}
                            >
                              Inspect
                            </button>
                            {activeIncident && (
                              <button
                                className="btn btn-primary btn-sm"
                                onClick={() => onSelectIncident(activeIncident.id)}
                              >
                                View Incident
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};
