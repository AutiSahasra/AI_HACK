import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  AlertTriangle, 
  FileText, 
  UploadCloud, 
  ShieldCheck, 
  Shield,
  Lock
} from 'lucide-react';
import { UserRole } from '../types';
import { canAccessRoute } from '../auth/permissions';

interface SidebarProps {
  userRole?: UserRole;
}

export const Sidebar: React.FC<SidebarProps> = ({ userRole }) => {
  const navItems = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/incidents', label: 'Incidents & RCA', icon: AlertTriangle },
    { to: '/logs', label: 'Log Explorer', icon: FileText },
    { to: '/upload', label: 'Upload Logs', icon: UploadCloud },
    { to: '/approvals', label: 'Approvals Queue', icon: ShieldCheck },
  ];

  // Strictly filter allowed items according to the centralized RBAC rules
  const allowedItems = navItems.filter(item => canAccessRoute(userRole, item.to));

  const getRoleTheme = (role?: UserRole) => {
    switch (role) {
      case 'approver':
        return { label: 'Senior Approver', color: '#b45309', bg: '#fef3c7' };
      case 'support_engineer':
        return { label: 'Support Engineer (L1/L2)', color: '#0369a1', bg: '#e0f2fe' };
      default:
        return { label: 'Guest / Unknown', color: '#475569', bg: '#f1f5f9' };
    }
  };

  const roleMeta = getRoleTheme(userRole);

  return (
    <aside style={{
      width: '240px',
      background: '#ffffff',
      borderRight: '1px solid var(--border-subtle)',
      display: 'flex',
      flexDirection: 'column',
      padding: '20px 14px',
      gap: '6px',
      justifyContent: 'space-between',
    }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <div style={{ padding: '0 10px 12px', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-dim)', fontWeight: 700 }}>
          Navigation
        </div>
        {allowedItems.map(item => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '10px 14px',
                borderRadius: '8px',
                color: isActive ? '#0f172a' : 'var(--text-muted)',
                background: isActive ? '#f1f5f9' : 'transparent',
                border: isActive ? '1px solid var(--border-subtle)' : '1px solid transparent',
                textDecoration: 'none',
                fontSize: '13px',
                fontWeight: isActive ? 600 : 500,
                transition: 'all 0.15s ease-in-out',
              })}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </div>

      {/* Access Tier Card at Bottom (styled like Paolo Upgrade Card) */}
      <div style={{
        marginTop: 'auto',
        padding: '14px',
        background: '#f8fafc',
        border: '1px solid var(--border-subtle)',
        borderRadius: '12px',
        fontSize: '12px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-dim)', marginBottom: '8px' }}>
          <Shield size={14} color={roleMeta.color} />
          <span style={{ fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', fontSize: '11px' }}>Access Tier</span>
        </div>
        <div style={{
          color: roleMeta.color,
          fontWeight: 600,
          background: roleMeta.bg,
          padding: '6px 10px',
          borderRadius: '6px',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          fontSize: '12px',
        }}>
          <Lock size={12} />
          <span>{roleMeta.label}</span>
        </div>
      </div>
    </aside>
  );
};
