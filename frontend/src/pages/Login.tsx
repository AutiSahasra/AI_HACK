import React, { useState } from 'react';
import { api, setToken, setStoredUser } from '../api/client';
import { User } from '../types';
import { Activity, KeyRound, User as UserIcon, Lock, AlertCircle } from 'lucide-react';

interface LoginProps {
  onLoginSuccess: (user: User) => void;
}

export const Login: React.FC<LoginProps> = ({ onLoginSuccess }) => {
  const [username, setUsername] = useState('support');
  const [password, setPassword] = useState('supportpassword123');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const resp = await api.login({ username, password });
      setToken(resp.access_token);
      setStoredUser(resp.user);
      onLoginSuccess(resp.user);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const setPresetUser = (u: string, p: string) => {
    setUsername(u);
    setPassword(p);
  };

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '24px',
      background: 'radial-gradient(ellipse at 50% 20%, rgba(56, 189, 248, 0.15), transparent 70%), var(--bg-primary)'
    }}>
      <div className="glass-panel" style={{ width: '100%', maxWidth: '440px', padding: '36px' }}>
        <div style={{ textAlign: 'center', marginBottom: '28px' }}>
          <div style={{
            width: '52px',
            height: '52px',
            borderRadius: '14px',
            background: 'var(--grad-primary)',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: '16px',
            boxShadow: 'var(--glow-cyan)'
          }}>
            <Activity size={28} color="#fff" />
          </div>
          <h2 style={{ fontSize: '24px', fontWeight: 700, marginBottom: '6px' }}>
            Welcome to RootCause Copilot
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Sign in to investigate incidents and manage safe remediation
          </p>
        </div>

        {error && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            padding: '12px',
            background: 'rgba(244, 63, 94, 0.12)',
            border: '1px solid rgba(244, 63, 94, 0.3)',
            borderRadius: '8px',
            color: '#fb7185',
            fontSize: '13px',
            marginBottom: '20px'
          }}>
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div>
            <label style={{ display: 'block', fontSize: '13px', color: 'var(--text-muted)', marginBottom: '6px' }}>
              Username
            </label>
            <div style={{ position: 'relative' }}>
              <input
                type="text"
                className="input-control"
                value={username}
                onChange={e => setUsername(e.target.value)}
                required
                style={{ paddingLeft: '38px' }}
              />
              <UserIcon size={16} color="var(--text-dim)" style={{ position: 'absolute', left: '12px', top: '12px' }} />
            </div>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '13px', color: 'var(--text-muted)', marginBottom: '6px' }}>
              Password
            </label>
            <div style={{ position: 'relative' }}>
              <input
                type="password"
                className="input-control"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                style={{ paddingLeft: '38px' }}
              />
              <Lock size={16} color="var(--text-dim)" style={{ position: 'absolute', left: '12px', top: '12px' }} />
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={loading}
            style={{ width: '100%', marginTop: '8px', padding: '12px' }}
          >
            <KeyRound size={16} />
            <span>{loading ? 'Authenticating...' : 'Sign In'}</span>
          </button>
        </form>

        <div style={{ marginTop: '28px', borderTop: '1px solid var(--border-subtle)', paddingTop: '20px' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-dim)', marginBottom: '10px', textAlign: 'center' }}>
            Quick Demo Logins (2 Roles Only):
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px' }}>
            <button
              type="button"
              onClick={() => setPresetUser('support', 'supportpassword123')}
              className="btn btn-secondary"
              style={{ fontSize: '12px', padding: '8px 10px', textAlign: 'center' }}
            >
              Support Engineer
            </button>
            <button
              type="button"
              onClick={() => setPresetUser('approver', 'approverpassword123')}
              className="btn btn-secondary"
              style={{ fontSize: '12px', padding: '8px 10px', textAlign: 'center' }}
            >
              Senior Approver
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
