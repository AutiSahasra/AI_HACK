import React from 'react';
import { UserRole } from '../types';
import { Permission, hasPermission } from '../auth/permissions';
import { Forbidden } from '../pages/Forbidden';

interface ProtectedRouteProps {
  userRole?: UserRole;
  allowedRoles?: UserRole[];
  requiredPermission?: Permission;
  children: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  userRole,
  allowedRoles,
  requiredPermission,
  children,
}) => {
  // If allowed roles are explicitly specified, check membership
  if (allowedRoles && userRole && !allowedRoles.includes(userRole)) {
    return <Forbidden userRole={userRole} requiredRoles={allowedRoles} />;
  }

  // If a specific permission is required, check via permissions system
  if (requiredPermission && !hasPermission(userRole, requiredPermission)) {
    return <Forbidden userRole={userRole} requiredRoles={allowedRoles} />;
  }

  return <>{children}</>;
};
