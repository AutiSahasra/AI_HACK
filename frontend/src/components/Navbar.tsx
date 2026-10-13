import React from 'react';
import { User } from '../types';
import { Shield, User as UserIcon, LogOut, Activity } from 'lucide-react';

interface NavbarProps {
  user: User | null;
  onLogout: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ user, onLogout }) => {
  const getRoleBadgeClass = (role?: string) => {
    switch (role) {
      case 'admin':
        return 'badge-critical';
      case 'approver':
        return 'badge-warn';
      default:
        return 'badge-info';
    }
  };

  return (
    <header style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '14px 28px',
      background: '#ffffff',
      borderBottom: '1px solid var(--border-subtle)',
      position: 'sticky',
      top: 0,
      zIndex: 40,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <div style={{
          width: '36px',
          height: '36px',
          borderRadius: '10px',
          background: '#0f172a',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
        }}>
          <Activity size={20} color="#fff" />
        </div>
        <div>
          <h1 style={{ fontSize: '17px', fontWeight: 700, margin: 0, letterSpacing: '-0.01em', color: '#0f172a' }}>
            RootCause <span style={{ fontWeight: 400, color: 'var(--text-muted)' }}>Copilot</span>
          </h1>
          <p style={{ fontSize: '11px', color: 'var(--text-dim)', margin: 0 }}>
            Incident Intelligence & Remediation Engine
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '18px' }}>
        {user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '6px 12px',
              background: '#f8fafc',
              borderRadius: '8px',
              border: '1px solid var(--border-subtle)'
            }}>
              <UserIcon size={16} color="var(--text-muted)" />
              <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-main)' }}>{user.full_name || user.username}</span>
              <span className={`badge ${getRoleBadgeClass(user.role)}`} style={{ fontSize: '11px', fontWeight: 600 }}>
                {user.role === 'approver' ? 'Senior Approver' : 'Support L1/L2'}
              </span>
            </div>
            
            <button
              onClick={onLogout}
              className="btn btn-secondary"
              style={{ padding: '6px 12px', fontSize: '13px' }}
              title="Sign Out"
            >
              <LogOut size={15} />
              <span>Logout</span>
            </button>
          </div>
        )}
      </div>
    </header>
  );
};
