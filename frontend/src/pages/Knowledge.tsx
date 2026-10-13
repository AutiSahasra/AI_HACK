import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Runbook, HistoricalIncident } from '../types';
import { BookOpen, History, CheckCircle, Search, ShieldCheck } from 'lucide-react';

export const Knowledge: React.FC = () => {
  const [runbooks, setRunbooks] = useState<Runbook[]>([]);
  const [historical, setHistorical] = useState<HistoricalIncident[]>([]);
  const [activeTab, setActiveTab] = useState<'runbooks' | 'historical'>('runbooks');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [rbRes, histRes] = await Promise.all([
        fetch('/api/incidents/knowledge/runbooks', {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        }).then(r => r.json()),
        fetch('/api/incidents/knowledge/historical', {
          headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        }).then(r => r.json()),
      ]);
      setRunbooks(Array.isArray(rbRes) ? rbRes : []);
      setHistorical(Array.isArray(histRes) ? histRes : []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const filteredRunbooks = runbooks.filter(r => 
    r.title?.toLowerCase().includes(search.toLowerCase()) || 
    r.service?.toLowerCase().includes(search.toLowerCase())
  );

  const filteredHistorical = historical.filter(h => 
    h.title?.toLowerCase().includes(search.toLowerCase()) || 
    h.service?.toLowerCase().includes(search.toLowerCase()) ||
    h.verifiedCause?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '22px', fontWeight: 700, marginBottom: '4px' }}>
            Operational Knowledge & Runbook Catalog
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Historical resolved incidents and approved remediation runbooks indexed for copilot retrieval.
          </p>
        </div>
      </div>

      {/* Tabs & Search */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            className={`btn ${activeTab === 'runbooks' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('runbooks')}
          >
            <BookOpen size={16} />
            <span>Approved Runbooks ({runbooks.length})</span>
          </button>
          <button
            className={`btn ${activeTab === 'historical' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('historical')}
          >
            <History size={16} />
            <span>Historical Incidents ({historical.length})</span>
          </button>
        </div>

        <div style={{ position: 'relative', width: '300px' }}>
          <input
            type="text"
            className="input-control"
            placeholder="Search catalog..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ paddingLeft: '36px' }}
          />
          <Search size={15} color="var(--text-dim)" style={{ position: 'absolute', left: '12px', top: '12px' }} />
        </div>
      </div>

      {/* Content */}
      {activeTab === 'runbooks' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {filteredRunbooks.map((rb, idx) => (
            <div key={idx} className="glass-panel" style={{ padding: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <span className="badge badge-info">{rb.service}</span>
                    <span className="badge badge-warn">Risk: {rb.riskLevel}</span>
                  </div>
                  <h3 style={{ fontSize: '16px', fontWeight: 600 }}>{rb.title}</h3>
                </div>
              </div>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '12px' }}>
                {rb.description}
              </p>
              <div style={{ background: 'var(--bg-secondary)', padding: '12px', borderRadius: '8px', marginBottom: '10px' }}>
                <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--accent-cyan)', marginBottom: '6px' }}>
                  Diagnostic Steps
                </div>
                <ul style={{ paddingLeft: '18px', fontSize: '13px', color: 'var(--text-main)' }}>
                  {rb.diagnosticSteps?.map((s, i) => <li key={i}>{s}</li>)}
                </ul>
              </div>
              {rb.recoveryCheck && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#34d399' }}>
                  <ShieldCheck size={16} />
                  <span>Recovery Check: {rb.recoveryCheck}</span>
                </div>
              )}
            </div>
          ))}
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {filteredHistorical.map((hi, idx) => (
            <div key={idx} className="glass-panel" style={{ padding: '20px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                    <span className="badge badge-info">{hi.service}</span>
                    <span className="badge badge-resolved">Verified Resolved</span>
                  </div>
                  <h3 style={{ fontSize: '16px', fontWeight: 600 }}>{hi.title}</h3>
                </div>
              </div>
              <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginBottom: '12px' }}>
                {hi.summary}
              </p>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
                <div style={{ background: '#f8fafc', border: '1px solid var(--border-subtle)', padding: '12px', borderRadius: '8px' }}>
                  <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 600 }}>VERIFIED CAUSE</div>
                  <div style={{ fontSize: '13px', color: 'var(--text-main)', marginTop: '4px' }}>{hi.verifiedCause}</div>
                </div>
                <div style={{ background: '#f8fafc', border: '1px solid var(--border-subtle)', padding: '12px', borderRadius: '8px' }}>
                  <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 600 }}>REMEDIATION PERFORMED</div>
                  <div style={{ fontSize: '13px', color: '#15803d', marginTop: '4px' }}>{hi.remediationPerformed}</div>
                </div>
              </div>
              {hi.logExcerpt && (
                <div>
                  <div style={{ fontSize: '11px', color: 'var(--text-dim)', fontWeight: 600, marginBottom: '4px' }}>LOG EXCERPT</div>
                  <div className="code-block">{hi.logExcerpt}</div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
