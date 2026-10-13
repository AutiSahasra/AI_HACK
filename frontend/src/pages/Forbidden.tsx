import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ShieldAlert, ArrowLeft, Lock, Info, LayoutDashboard } from 'lucide-react';
import { UserRole } from '../types';
import { getRoleDisplayName, ROUTE_ACCESS } from '../auth/permissions';

interface ForbiddenProps {
  userRole?: UserRole;
  requiredRoles?: UserRole[];
  resourceName?: string;
}

export const Forbidden: React.FC<ForbiddenProps> = ({
  userRole,
  requiredRoles,
  resourceName,
}) => {
  const navigate = useNavigate();
  const location = useLocation();

  const currentPath = location.pathname;
  const routeMeta = ROUTE_ACCESS[currentPath];
  const targetName = resourceName || routeMeta?.description || currentPath;
  const neededRoles = requiredRoles || routeMeta?.requiredRoles || ['approver'];

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '70vh',
      padding: '40px 20px',
      textAlign: 'center',
    }}>
      <div style={{
        maxWidth: '560px',
        width: '100%',
        background: 'rgba(22, 29, 49, 0.75)',
        border: '1px solid rgba(244, 63, 94, 0.3)',
        borderRadius: '16px',
        padding: '36px 32px',
        boxShadow: '0 12px 40px rgba(0, 0, 0, 0.5), 0 0 24px rgba(244, 63, 94, 0.15)',
        backdropFilter: 'blur(16px)',
        position: 'relative',
        overflow: 'hidden',
      }}>
        {/* Glow ambient header */}
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: '4px',
          background: 'linear-gradient(90deg, #f43f5e 0%, #e11d48 50%, #f43f5e 100%)',
        }} />

        <div style={{
          width: '64px',
          height: '64px',
          borderRadius: '16px',
          background: 'rgba(244, 63, 94, 0.12)',
          border: '1px solid rgba(244, 63, 94, 0.25)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 20px',
          color: 'var(--accent-rose)',
        }}>
          <ShieldAlert size={34} />
        </div>

        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '6px',
          background: 'rgba(244, 63, 94, 0.15)',
          color: '#fda4af',
          fontSize: '11px',
          fontWeight: 700,
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          padding: '4px 10px',
          borderRadius: '999px',
          marginBottom: '12px',
        }}>
          <Lock size={12} />
          <span>HTTP 403 • Access Denied</span>
        </div>

        <h2 style={{ fontSize: '24px', fontWeight: 700, color: 'var(--text-main)', marginBottom: '10px' }}>
          Restricted Security Workspace
        </h2>

        <p style={{ fontSize: '14px', color: 'var(--text-muted)', marginBottom: '24px', lineHeight: 1.6 }}>
          You do not have the required permissions to access <strong>{targetName}</strong>. 
          This endpoint requires elevated role privileges.
        </p>

        {/* Role breakdown info card */}
        <div style={{
          background: 'rgba(16, 21, 36, 0.7)',
          border: '1px solid var(--border-subtle)',
          borderRadius: '10px',
          padding: '16px',
          textAlign: 'left',
          marginBottom: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '10px',
          fontSize: '13px',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Info size={14} /> Your Current Role:
            </span>
            <span style={{
              background: 'rgba(56, 189, 248, 0.15)',
              color: 'var(--accent-cyan)',
              padding: '2px 8px',
              borderRadius: '6px',
              fontWeight: 600,
              fontSize: '12px',
            }}>
              {getRoleDisplayName(userRole)}
            </span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ color: 'var(--text-dim)' }}>Authorized Roles:</span>
            <span style={{
              color: 'var(--text-main)',
              fontWeight: 600,
              fontSize: '12px',
            }}>
              {neededRoles.map(r => getRoleDisplayName(r)).join(' or ')}
            </span>
          </div>

          <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '8px', color: 'var(--text-dim)', fontSize: '12px' }}>
            Path: <code style={{ color: '#f8fafc', background: 'rgba(0,0,0,0.3)', padding: '2px 6px', borderRadius: '4px' }}>{currentPath}</code>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
          <button
            onClick={() => navigate('/')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 18px',
              borderRadius: '8px',
              background: 'var(--grad-primary)',
              border: 'none',
              color: '#fff',
              fontSize: '14px',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'opacity 0.2s',
            }}
          >
            <LayoutDashboard size={16} />
            <span>Return to Dashboard</span>
          </button>
          
          <button
            onClick={() => navigate(-1)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 18px',
              borderRadius: '8px',
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-muted)',
              fontSize: '14px',
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            <ArrowLeft size={16} />
            <span>Go Back</span>
          </button>
        </div>
      </div>
    </div>
  );
};
