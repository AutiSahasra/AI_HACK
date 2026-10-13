import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { Incident, IncidentStatus, LogSeverity } from '../types';
import { AlertTriangle, Clock, RefreshCw, Filter, Layers, ChevronRight, CheckCircle2, ShieldAlert } from 'lucide-react';

export const Incidents: React.FC = () => {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedStatus, setSelectedStatus] = useState<string>('');
  const [selectedSeverity, setSelectedSeverity] = useState<string>('');
  const [selectedService, setSelectedService] = useState<string>('');

  const fetchIncidents = async () => {
    setLoading(true);
    try {
      const data = await api.getIncidents({
        status: selectedStatus || undefined,
        severity: selectedSeverity || undefined,
        service: selectedService || undefined,
      });
      setIncidents(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIncidents();
    const interval = setInterval(fetchIncidents, 6000);
    return () => clearInterval(interval);
  }, [selectedStatus, selectedSeverity, selectedService]);

  const getStatusBadge = (status: IncidentStatus) => {
    switch (status) {
      case 'resolved':
        return <span className="badge badge-resolved">Resolved</span>;
      case 'escalated':
        return <span className="badge badge-critical">Escalated</span>;
      case 'remediating':
      case 'verifying':
        return <span className="badge badge-warn">{status}</span>;
      case 'analyzing':
      case 'analyzed':
        return <span className="badge badge-info">{status}</span>;
      default:
        return <span className="badge badge-info">{status}</span>;
    }
  };

  const getSeverityBadge = (severity: LogSeverity) => {
    switch (severity) {
      case 'CRITICAL':
        return <span className="badge badge-critical">CRITICAL</span>;
      case 'ERROR':
        return <span className="badge badge-error">ERROR</span>;
      case 'WARN':
        return <span className="badge badge-warn">WARN</span>;
      default:
        return <span className="badge badge-info">{severity}</span>;
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '22px', fontWeight: 700, marginBottom: '4px' }}>
            Incident Intelligence Feed
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Correlated candidate incidents automatically grouped by service, pattern signatures, and temporal windows.
          </p>
        </div>
        <button onClick={fetchIncidents} className="btn btn-secondary" disabled={loading}>
          <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Filters */}
      <div className="glass-panel" style={{ padding: '16px', display: 'flex', gap: '12px' }}>
        <select
          className="input-control"
          value={selectedStatus}
          onChange={e => setSelectedStatus(e.target.value)}
          style={{ maxWidth: '200px' }}
        >
          <option value="">All Statuses</option>
          <option value="new">New</option>
          <option value="analyzing">Analyzing</option>
          <option value="analyzed">Analyzed</option>
          <option value="awaiting_approval">Awaiting Approval</option>
          <option value="remediating">Remediating</option>
          <option value="verifying">Verifying</option>
          <option value="resolved">Resolved</option>
          <option value="escalated">Escalated</option>
        </select>

        <select
          className="input-control"
          value={selectedSeverity}
          onChange={e => setSelectedSeverity(e.target.value)}
          style={{ maxWidth: '200px' }}
        >
          <option value="">All Severities</option>
          <option value="CRITICAL">CRITICAL</option>
          <option value="ERROR">ERROR</option>
          <option value="WARN">WARN</option>
        </select>

        <input
          type="text"
          placeholder="Filter by service name..."
          className="input-control"
          value={selectedService}
          onChange={e => setSelectedService(e.target.value)}
          style={{ maxWidth: '240px' }}
        />
      </div>

      {/* Incident List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {incidents.length === 0 ? (
          <div className="glass-panel" style={{ textAlign: 'center', padding: '48px', color: 'var(--text-dim)' }}>
            <Layers size={36} style={{ marginBottom: '12px', opacity: 0.5 }} />
            <div style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-main)' }}>No Active Incidents Found</div>
            <p style={{ fontSize: '13px', marginTop: '4px' }}>
              Upload error logs in CSV/JSON/LOG formats to observe automated correlation.
            </p>
          </div>
        ) : (
          incidents.map(inc => {
            const id = inc.id || (inc as any)._id;
            return (
              <Link
                key={id}
                to={`/incidents/${id}`}
                className="glass-panel"
                style={{
                  padding: '20px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  textDecoration: 'none',
                  color: 'inherit',
                  transition: 'all 0.2s',
                  borderLeft: inc.isRepeated ? '4px solid #ef4444' : '4px solid var(--accent-blue)'
                }}
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxWidth: '80%' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    {getSeverityBadge(inc.severity)}
                    {getStatusBadge(inc.status)}
                    <span style={{ fontWeight: 700, color: 'var(--accent-blue)', fontSize: '14px' }}>
                      {inc.service}
                    </span>
                    {inc.isRepeated && (
                      <span className="badge badge-critical" style={{ fontSize: '10px' }}>
                        Repeated Alert
                      </span>
                    )}
                  </div>

                  <h3 style={{ fontSize: '16px', margin: 0, color: 'var(--text-main)' }}>
                    {inc.title}
                  </h3>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '12px', color: 'var(--text-dim)' }}>
                    <span>
                      <strong>{inc.eventCount}</strong> correlated events
                    </span>
                    <span>•</span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Clock size={13} />
                      First: {new Date(inc.firstSeen).toLocaleTimeString()}
                    </span>
                    <span>•</span>
                    <span>
                      Last: {new Date(inc.lastSeen).toLocaleTimeString()}
                    </span>
                    {inc.matchedRules && inc.matchedRules.length > 0 && (
                      <>
                        <span>•</span>
                        <span style={{ color: 'var(--text-muted)' }}>
                          Rule: {inc.matchedRules.join(', ')}
                        </span>
                      </>
                    )}
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--accent-cyan)' }}>
                  <span style={{ fontSize: '13px', fontWeight: 600 }}>Investigate</span>
                  <ChevronRight size={18} />
                </div>
              </Link>
            );
          })
        )}
      </div>
    </div>
  );
};
