import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { AuditLogEntry } from '../types';
import { ScrollText, RefreshCw, Filter, ShieldCheck, User, Clock } from 'lucide-react';

export const AuditLog: React.FC = () => {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [actorFilter, setActorFilter] = useState('');

  const fetchAuditLogs = async () => {
    setLoading(true);
    try {
      const data = await api.getAuditLogs(100);
      setLogs(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditLogs();
    const interval = setInterval(fetchAuditLogs, 6000);
    return () => clearInterval(interval);
  }, []);

  const filteredLogs = logs.filter(l => 
    !actorFilter || l.actor.toLowerCase().includes(actorFilter.toLowerCase())
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '22px', fontWeight: 700, marginBottom: '4px' }}>
            Append-Only Audit Trail
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Immutable security ledger tracking user logins, approval decisions, executed remediations, and verification outcomes.
          </p>
        </div>
        <button onClick={fetchAuditLogs} className="btn btn-secondary" disabled={loading}>
          <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      <div className="glass-panel" style={{ padding: '16px', display: 'flex', gap: '12px' }}>
        <input
          type="text"
          className="input-control"
          placeholder="Filter by actor (username or system)..."
          value={actorFilter}
          onChange={e => setActorFilter(e.target.value)}
          style={{ maxWidth: '320px' }}
        />
      </div>

      <div className="glass-panel" style={{ padding: '20px' }}>
        <h3 style={{ fontSize: '16px', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ScrollText size={18} color="var(--accent-cyan)" />
          <span>Ledger Records ({filteredLogs.length})</span>
        </h3>

        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Action</th>
                <th>Actor</th>
                <th>Role</th>
                <th>Target Entity</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '32px', color: 'var(--text-dim)' }}>
                    No audit records match your criteria.
                  </td>
                </tr>
              ) : (
                filteredLogs.map(l => (
                  <tr key={l.id}>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', whiteSpace: 'nowrap' }}>
                      {new Date(l.timestamp).toLocaleTimeString()}
                    </td>
                    <td>
                      <span className="badge badge-info" style={{ fontSize: '11px', fontFamily: 'var(--font-mono)' }}>
                        {l.action}
                      </span>
                    </td>
                    <td style={{ fontWeight: 600 }}>{l.actor}</td>
                    <td>
                      <span style={{ fontSize: '12px', color: 'var(--text-dim)' }}>{l.role}</span>
                    </td>
                    <td>
                      <span style={{ fontSize: '12px', fontFamily: 'var(--font-mono)', color: 'var(--accent-cyan)' }}>
                        {l.entityType}:{l.entityId?.slice(0, 8)}...
                      </span>
                    </td>
                    <td>
                      <span style={{ fontSize: '12px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                        {JSON.stringify(l.details)}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
