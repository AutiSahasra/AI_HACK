import { UserRole } from '../types';

export type Permission =
  | 'VIEW_DASHBOARD'
  | 'UPLOAD_LOGS'
  | 'VIEW_LOGS'
  | 'VIEW_INCIDENTS'
  | 'REQUEST_REMEDIATION'
  | 'SEND_APPROVAL_REQUEST'
  | 'VIEW_MY_REQUESTS'
  | 'VIEW_TICKETS'
  | 'UPDATE_TICKETS'
  | 'ADMIN_TICKET_OVERRIDE'
  | 'VIEW_KNOWLEDGE'
  | 'SUBMIT_FEEDBACK'
  | 'VIEW_APPROVALS'
  | 'VIEW_APPROVALS_QUEUE'
  | 'DECIDE_APPROVAL'
  | 'APPROVE_REQUEST'
  | 'REJECT_REQUEST'
  | 'EXECUTE_REMEDIATION'
  | 'DIRECT_EXECUTE_REMEDIATION'
  | 'VIEW_AUDIT'
  | 'MANAGE_SOURCES'
  | 'MANAGE_RULES'
  | 'EXECUTE_RETENTION'
  | 'CHAOS_CONTROLS';

const COMMON_PERMISSIONS: Permission[] = [
  'VIEW_DASHBOARD',
  'VIEW_LOGS',
  'VIEW_INCIDENTS',
  'VIEW_TICKETS',
  'UPDATE_TICKETS',
  'VIEW_KNOWLEDGE',
  'SUBMIT_FEEDBACK',
];

export const ROLE_PERMISSIONS: Record<UserRole, Set<Permission>> = {
  support_engineer: new Set<Permission>([
    ...COMMON_PERMISSIONS,
    'UPLOAD_LOGS',
    'REQUEST_REMEDIATION',
    'SEND_APPROVAL_REQUEST',
    'VIEW_MY_REQUESTS',
  ]),
  approver: new Set<Permission>([
    ...COMMON_PERMISSIONS,
    'VIEW_APPROVALS',
    'VIEW_APPROVALS_QUEUE',
    'DECIDE_APPROVAL',
    'APPROVE_REQUEST',
    'REJECT_REQUEST',
    'EXECUTE_REMEDIATION',
    'DIRECT_EXECUTE_REMEDIATION',
    'CHAOS_CONTROLS',
  ]),
};

export const ROUTE_ACCESS: Record<string, { requiredRoles: UserRole[]; description: string }> = {
  '/': { requiredRoles: ['support_engineer', 'approver'], description: 'System Dashboard' },
  '/upload': { requiredRoles: ['support_engineer'], description: 'Log Upload & Batch Ingestion' },
  '/logs': { requiredRoles: ['support_engineer', 'approver'], description: 'Log Explorer' },
  '/incidents': { requiredRoles: ['support_engineer', 'approver'], description: 'Incident Investigation & RCA' },
  '/approvals': { requiredRoles: ['approver'], description: 'Remediation Approvals Queue' },
};

export const hasPermission = (role: UserRole | undefined, permission: Permission): boolean => {
  if (!role) return false;
  return ROLE_PERMISSIONS[role]?.has(permission) ?? false;
};

export const canAccessRoute = (role: UserRole | undefined, path: string): boolean => {
  if (!role) return false;
  // Match prefix or exact
  const cleanPath = path.split('?')[0].split('#')[0];
  for (const [routePattern, config] of Object.entries(ROUTE_ACCESS)) {
    if (routePattern === '/' && cleanPath === '/') {
      return config.requiredRoles.includes(role);
    }
    if (routePattern !== '/' && (cleanPath === routePattern || cleanPath.startsWith(routePattern + '/'))) {
      return config.requiredRoles.includes(role);
    }
  }
  return false; // Only explicitly permitted routes in ROUTE_ACCESS are allowed
};

export const getRoleDisplayName = (role: UserRole | undefined): string => {
  switch (role) {
    case 'approver':
      return 'Senior Approver';
    case 'support_engineer':
      return 'Support Engineer (L1/L2)';
    default:
      return 'Unknown Role';
  }
};
