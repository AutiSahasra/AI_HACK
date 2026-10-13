import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  AlertTriangle, 
  FileText, 
  UploadCloud, 
  TicketCheck, 
  ShieldCheck, 
  ScrollText, 
  BookOpen, 
  Settings,
  Shield,
  Lock
} from 'lucide-react';
import { UserRole } from '../types';
import { canAccessRoute, getRoleDisplayName } from '../auth/permissions';

interface SidebarProps {
  userRole?: UserRole;
}

export const Sidebar: React.FC<SidebarProps> = ({ userRole }) => {
  const navItems = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/incidents', label: 'Incidents & RCA', icon: AlertTriangle },
    { to: '/logs', label: 'Log Explorer', icon: FileText },
    { to: '/upload', label: 'Upload Logs', icon: UploadCloud },
    { to: '/tickets', label: 'Tickets', icon: TicketCheck },
    { to: '/approvals', label: 'Approvals Queue', icon: ShieldCheck },
    { to: '/audit', label: 'Audit Trail', icon: ScrollText },
    { to: '/knowledge', label: 'Runbooks & Past RCA', icon: BookOpen },
    { to: '/admin', label: 'Settings & Sources', icon: Settings },
  ];

  // Strictly filter allowed items according to the centralized RBAC rules
  const allowedItems = navItems.filter(item => canAccessRoute(userRole, item.to));

  const getRoleTheme = (role?: UserRole) => {
    switch (role) {
      case 'admin':
        return { label: 'Administrator', color: '#f43f5e', bg: 'rgba(244, 63, 94, 0.12)' };
      case 'approver':
        return { label: 'Senior Approver', color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.12)' };
      case 'support_engineer':
        return { label: 'Support Engineer (L1/L2)', color: '#38bdf8', bg: 'rgba(56, 189, 248, 0.12)' };
      default:
        return { label: 'Guest / Unknown', color: '#94a3b8', bg: 'rgba(255, 255, 255, 0.05)' };
    }
  };

  const roleMeta = getRoleTheme(userRole);

  return (
    <aside style={{
      width: '240px',
      background: 'rgba(16, 21, 36, 0.6)',
      borderRight: '1px solid var(--border-subtle)',
      display: 'flex',
      flexDirection: 'column',
      padding: '20px 12px',
      gap: '6px',
      justifyContent: 'space-between',
    }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        <div style={{ padding: '0 12px 14px', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-dim)', fontWeight: 600 }}>
          Workspace Navigation
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
                color: isActive ? '#fff' : 'var(--text-muted)',
                background: isActive ? 'rgba(56, 189, 248, 0.12)' : 'transparent',
                border: isActive ? '1px solid var(--border-accent)' : '1px solid transparent',
                textDecoration: 'none',
                fontSize: '14px',
                fontWeight: isActive ? 600 : 500,
                transition: 'all 0.15s',
              })}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </div>

      {/* Role Indicator Card at Bottom */}
      <div style={{
        marginTop: 'auto',
        padding: '12px',
        background: 'rgba(10, 13, 20, 0.6)',
        border: '1px solid var(--border-subtle)',
        borderRadius: '8px',
        fontSize: '11px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-dim)', marginBottom: '4px' }}>
          <Shield size={12} color={roleMeta.color} />
          <span style={{ fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Access Tier</span>
        </div>
        <div style={{
          color: roleMeta.color,
          fontWeight: 600,
          background: roleMeta.bg,
          padding: '4px 8px',
          borderRadius: '4px',
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
        }}>
          <Lock size={11} />
          <span>{roleMeta.label}</span>
        </div>
      </div>
    </aside>
  );
};
