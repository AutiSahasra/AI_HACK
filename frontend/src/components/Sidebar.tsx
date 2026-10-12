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
  Settings 
} from 'lucide-react';
import { UserRole } from '../types';

interface SidebarProps {
  userRole?: UserRole;
}

export const Sidebar: React.FC<SidebarProps> = ({ userRole }) => {
  const navItems = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/incidents', label: 'Incidents', icon: AlertTriangle },
    { to: '/logs', label: 'Log Explorer', icon: FileText },
    { to: '/upload', label: 'Upload Logs', icon: UploadCloud },
    { to: '/tickets', label: 'Tickets', icon: TicketCheck },
    { to: '/approvals', label: 'Approvals', icon: ShieldCheck, roleRequired: ['approver', 'admin'] },
    { to: '/audit', label: 'Audit Trail', icon: ScrollText, roleRequired: ['approver', 'admin'] },
    { to: '/knowledge', label: 'Runbooks & Past RCA', icon: BookOpen },
    { to: '/admin', label: 'Settings & Sources', icon: Settings, roleRequired: ['admin'] },
  ];

  const allowedItems = navItems.filter(item => {
    if (!item.roleRequired) return true;
    return userRole && item.roleRequired.includes(userRole);
  });

  return (
    <aside style={{
      width: '240px',
      background: 'rgba(16, 21, 36, 0.6)',
      borderRight: '1px solid var(--border-subtle)',
      display: 'flex',
      flexDirection: 'column',
      padding: '20px 12px',
      gap: '6px',
    }}>
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
    </aside>
  );
};
