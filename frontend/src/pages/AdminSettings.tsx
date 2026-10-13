import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Radio, RefreshCw, Key, Settings, ShieldCheck, ToggleLeft, ToggleRight, Plus } from 'lucide-react';

export const AdminSettings: React.FC = () => {
  const [sources, setSources] = useState<any[]>([]);
  const [rules, setRules] = useState<any[]>([]);
  const [newSourceName, setNewSourceName] = useState('');
  const [generatedKey, setGeneratedKey] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchAdminData = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const [srcRes, rulesRes] = await Promise.all([
        fetch('/api/admin/sources', { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
        fetch('/api/admin/rules', { headers: { Authorization: `Bearer ${token}` } }).then(r => r.json()),
      ]);
      setSources(Array.isArray(srcRes) ? srcRes : []);
      setRules(Array.isArray(rulesRes) ? rulesRes : []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAdminData();
    const interval = setInterval(fetchAdminData, 6000);
    return () => clearInterval(interval);
  }, []);

  const handleCreateSource = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newSourceName.trim()) return;
    try {
      const token = localStorage.getItem('token');
      const res = await fetch('/api/admin/sources', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ name: newSourceName.trim(), description: 'Collector stream' })
      }).then(r => r.json());
      setGeneratedKey(res.apiKey);
      setNewSourceName('');
      fetchAdminData();
    } catch (e) {
      console.error(e);
    }
  };

  const handleToggleRule = async (ruleId: string, currentEnabled: boolean) => {
    try {
      const token = localStorage.getItem('token');
      await fetch(`/api/admin/rules/${ruleId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({ enabled: !currentEnabled })
      });
      fetchAdminData();
    } catch (e) {
      console.error(e);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '22px', fontWeight: 700, marginBottom: '4px' }}>
            System Settings & Log Source Administration
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Manage streaming log collectors, API key credentials, and active detection rules.
          </p>
        </div>
        <button onClick={fetchAdminData} className="btn btn-secondary" disabled={loading}>
          <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Live Sources Panel */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <h3 style={{ fontSize: '17px', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Radio size={18} color="var(--accent-cyan)" />
          <span>Configured Live Streaming Sources ({sources.length})</span>
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '14px', marginBottom: '24px' }}>
          {sources.length === 0 ? (
            <div style={{ padding: '16px', color: 'var(--text-dim)', fontSize: '13px' }}>
              No live sources streaming currently. Start the collector or register one below.
            </div>
          ) : (
            sources.map(src => (
              <div key={src.sourceId || src.name} style={{ background: '#f8fafc', padding: '16px', borderRadius: '10px', border: '1px solid var(--border-subtle)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <span style={{ fontWeight: 600, color: 'var(--text-main)', fontSize: '14px' }}>{src.name}</span>
                  <span className={`badge ${src.status === 'active' ? 'badge-resolved' : 'badge-info'}`}>
                    {src.status}
                  </span>
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-dim)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <div>Last Seen: {src.lastSeenAt ? new Date(src.lastSeenAt).toLocaleTimeString() : 'Never'}</div>
                  <div>Total Ingested Events: <strong style={{ color: 'var(--text-main)' }}>{src.eventCount || 0}</strong></div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Register Source Form */}
        <form onSubmit={handleCreateSource} style={{ display: 'flex', gap: '10px', alignItems: 'center', maxWidth: '540px' }}>
          <input
            type="text"
            className="input-control"
            placeholder="New source identifier (e.g. k8s-order-service)..."
            value={newSourceName}
            onChange={e => setNewSourceName(e.target.value)}
          />
          <button type="submit" className="btn btn-primary" style={{ whiteSpace: 'nowrap' }}>
            <Plus size={16} /> Register Source
          </button>
        </form>

        {generatedKey && (
          <div style={{ marginTop: '16px', padding: '12px 16px', background: '#f8fafc', border: '1px solid var(--border-subtle)', borderRadius: '8px', fontSize: '13px' }}>
            <strong style={{ color: 'var(--text-main)' }}>Generated API Key:</strong> <code style={{ color: '#0f172a', fontWeight: 600, marginLeft: '8px', background: '#ffffff', padding: '2px 6px', borderRadius: '4px', border: '1px solid var(--border-subtle)' }}>{generatedKey}</code>
            <div style={{ fontSize: '11px', color: 'var(--text-dim)', marginTop: '4px' }}>
              Pass this key in the <code>X-API-Key</code> HTTP header when POSTing to <code>/api/ingest</code>.
            </div>
          </div>
        )}
      </div>

      {/* Detection Rules Panel */}
      <div className="glass-panel" style={{ padding: '24px' }}>
        <h3 style={{ fontSize: '17px', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--text-main)' }}>
          <ShieldCheck size={18} color="var(--text-main)" />
          <span>Active Detection Rules</span>
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {rules.map(rule => (
            <div key={rule.id || rule._id} style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '14px 18px',
              background: '#f8fafc',
              borderRadius: '8px',
              border: '1px solid var(--border-subtle)'
            }}>
              <div style={{ maxWidth: '75%' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                  <span style={{ fontWeight: 600, color: 'var(--text-main)', fontSize: '14px' }}>{rule.name}</span>
                  <span className="badge badge-info" style={{ fontSize: '10px' }}>{rule.ruleType}</span>
                  <span className={`badge badge-${rule.severity?.toLowerCase()}`} style={{ fontSize: '10px' }}>{rule.severity}</span>
                </div>
                <p style={{ fontSize: '12px', color: 'var(--text-muted)', margin: 0 }}>
                  {rule.description} (Threshold: {rule.threshold} in {rule.windowMinutes}m)
                </p>
              </div>

              <button
                className={`btn ${rule.enabled ? 'btn-success' : 'btn-secondary'}`}
                style={{ padding: '6px 12px', fontSize: '12px' }}
                onClick={() => handleToggleRule(rule.id || rule._id, rule.enabled)}
              >
                {rule.enabled ? 'Enabled' : 'Disabled'}
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
