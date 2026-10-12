import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { LogEvent, LogSeverity } from '../types';
import { Search, Filter, ShieldAlert, ChevronDown, ChevronRight, RefreshCw, Hash, Database } from 'lucide-react';

export const LogExplorer: React.FC = () => {
  const [logs, setLogs] = useState<LogEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [services, setServices] = useState<string[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState('');
  const [selectedService, setSelectedService] = useState('');
  const [selectedSeverity, setSelectedSeverity] = useState('');
  const [selectedSourceType, setSelectedSourceType] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 50;

  const fetchServices = async () => {
    try {
      const data = await api.getServices();
      setServices(data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const resp = await api.getLogs({
        search: search || undefined,
        service: selectedService || undefined,
        severity: selectedSeverity || undefined,
        source_type: selectedSourceType || undefined,
        page,
        page_size: pageSize,
      });
      setLogs(resp.items);
      setTotal(resp.total);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchServices();
  }, []);

  useEffect(() => {
    fetchLogs();
  }, [page, selectedService, selectedSeverity, selectedSourceType]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchLogs();
  };

  const getSeverityBadge = (severity: LogSeverity) => {
    switch (severity) {
      case 'CRITICAL':
        return <span className="badge badge-critical">CRITICAL</span>;
      case 'ERROR':
        return <span className="badge badge-error">ERROR</span>;
      case 'WARN':
        return <span className="badge badge-warn">WARN</span>;
      case 'INFO':
        return <span className="badge badge-info">INFO</span>;
      default:
        return <span className="badge">{severity}</span>;
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '22px', fontWeight: 700, marginBottom: '4px' }}>
            Unified Log Explorer
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Real-time normalized stream from manual uploads and live collectors with automatic secret masking.
          </p>
        </div>
        <button onClick={fetchLogs} className="btn btn-secondary" disabled={loading}>
          <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Filter Bar */}
      <div className="glass-panel" style={{ padding: '16px' }}>
        <form onSubmit={handleSearchSubmit} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr auto', gap: '12px' }}>
          <div style={{ position: 'relative' }}>
            <input
              type="text"
              placeholder="Full text search message content..."
              className="input-control"
              value={search}
              onChange={e => setSearch(e.target.value)}
              style={{ paddingLeft: '38px' }}
            />
            <Search size={16} color="var(--text-dim)" style={{ position: 'absolute', left: '12px', top: '12px' }} />
          </div>

          <select
            className="input-control"
            value={selectedService}
            onChange={e => { setSelectedService(e.target.value); setPage(1); }}
          >
            <option value="">All Services</option>
            {services.map(s => <option key={s} value={s}>{s}</option>)}
          </select>

          <select
            className="input-control"
            value={selectedSeverity}
            onChange={e => { setSelectedSeverity(e.target.value); setPage(1); }}
          >
            <option value="">All Severities</option>
            <option value="CRITICAL">CRITICAL</option>
            <option value="ERROR">ERROR</option>
            <option value="WARN">WARN</option>
            <option value="INFO">INFO</option>
            <option value="DEBUG">DEBUG</option>
          </select>

          <select
            className="input-control"
            value={selectedSourceType}
            onChange={e => { setSelectedSourceType(e.target.value); setPage(1); }}
          >
            <option value="">All Sources</option>
            <option value="manual_upload">Manual Upload</option>
            <option value="live">Live Stream</option>
          </select>

          <button type="submit" className="btn btn-primary">
            Filter
          </button>
        </form>
      </div>

      {/* Logs Table */}
      <div className="glass-panel" style={{ padding: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', padding: '0 4px' }}>
          <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Showing <strong>{logs.length}</strong> of <strong>{total}</strong> normalized events
          </span>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              className="btn btn-secondary"
              disabled={page <= 1}
              onClick={() => setPage(p => Math.max(1, p - 1))}
              style={{ padding: '4px 10px', fontSize: '12px' }}
            >
              Previous
            </button>
            <span style={{ fontSize: '12px', display: 'flex', alignItems: 'center', padding: '0 6px' }}>
              Page {page}
            </span>
            <button
              className="btn btn-secondary"
              disabled={page * pageSize >= total}
              onClick={() => setPage(p => p + 1)}
              style={{ padding: '4px 10px', fontSize: '12px' }}
            >
              Next
            </button>
          </div>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: '30px' }}></th>
                <th>Timestamp</th>
                <th>Severity</th>
                <th>Service</th>
                <th>Message</th>
                <th>Source</th>
                <th>Security</th>
              </tr>
            </thead>
            <tbody>
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', color: 'var(--text-dim)', padding: '32px' }}>
                    {loading ? 'Fetching log events...' : 'No logs found matching your filters.'}
                  </td>
                </tr>
              ) : (
                logs.map(log => {
                  const id = log.id || log._id || '';
                  const isExpanded = expandedId === id;
                  return (
                    <React.Fragment key={id}>
                      <tr
                        onClick={() => setExpandedId(isExpanded ? null : id)}
                        style={{
                          cursor: 'pointer',
                          background: isExpanded ? 'rgba(56, 189, 248, 0.05)' : undefined
                        }}
                      >
                        <td>
                          {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                        </td>
                        <td style={{ fontFamily: 'var(--font-mono)', fontSize: '12px', whiteSpace: 'nowrap' }}>
                          {new Date(log.timestamp).toISOString()}
                        </td>
                        <td>{getSeverityBadge(log.severity)}</td>
                        <td style={{ fontWeight: 600, color: 'var(--accent-cyan)' }}>
                          {log.service}
                        </td>
                        <td style={{
                          maxWidth: '540px',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          fontFamily: 'var(--font-mono)',
                          fontSize: '13px'
                        }}>
                          {log.message.split('\n')[0]}
                        </td>
                        <td style={{ fontSize: '12px', color: 'var(--text-dim)' }}>
                          {log.source.type === 'live' ? 'Live Stream' : 'File Upload'}
                        </td>
                        <td>
                          {log.redacted ? (
                            <span className="badge badge-resolved" style={{ fontSize: '10px' }} title="Credentials/Secrets masked">
                              <ShieldAlert size={10} /> Redacted
                            </span>
                          ) : (
                            <span style={{ fontSize: '11px', color: 'var(--text-dim)' }}>Clear</span>
                          )}
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr>
                          <td colSpan={7} style={{ padding: '16px', background: 'rgba(6, 9, 14, 0.6)' }}>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                              <div>
                                <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
                                  Full Message / Stack Trace
                                </div>
                                <div className="code-block" style={{ whiteSpace: 'pre-wrap' }}>
                                  {log.message}
                                </div>
                              </div>
                              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
                                <div style={{ background: 'var(--bg-secondary)', padding: '10px', borderRadius: '6px' }}>
                                  <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>FINGERPRINT</div>
                                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                    {log.fingerprint}
                                  </div>
                                </div>
                                <div style={{ background: 'var(--bg-secondary)', padding: '10px', borderRadius: '6px' }}>
                                  <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>TRACE ID</div>
                                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                                    {log.traceId || 'None'}
                                  </div>
                                </div>
                                <div style={{ background: 'var(--bg-secondary)', padding: '10px', borderRadius: '6px' }}>
                                  <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>REQUEST ID</div>
                                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: '12px' }}>
                                    {log.requestId || 'None'}
                                  </div>
                                </div>
                                <div style={{ background: 'var(--bg-secondary)', padding: '10px', borderRadius: '6px' }}>
                                  <div style={{ fontSize: '11px', color: 'var(--text-dim)' }}>SOURCE ID</div>
                                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                    {log.source.sourceId}
                                  </div>
                                </div>
                              </div>
                              {log.attributes && Object.keys(log.attributes).length > 0 && (
                                <div>
                                  <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
                                    Structured Attributes
                                  </div>
                                  <div className="code-block">
                                    {JSON.stringify(log.attributes, null, 2)}
                                  </div>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
