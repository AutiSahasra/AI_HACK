import { describe, it, expect } from 'vitest';
import { hasPermission, canAccessRoute, getRoleDisplayName } from './permissions';

describe('Role-Based Access Control (RBAC) System', () => {
  describe('Support Engineer Role (support_engineer)', () => {
    it('has permission for incident triage and log exploration', () => {
      expect(hasPermission('support_engineer', 'VIEW_DASHBOARD')).toBe(true);
      expect(hasPermission('support_engineer', 'UPLOAD_LOGS')).toBe(true);
      expect(hasPermission('support_engineer', 'VIEW_LOGS')).toBe(true);
      expect(hasPermission('support_engineer', 'VIEW_INCIDENTS')).toBe(true);
      expect(hasPermission('support_engineer', 'REQUEST_REMEDIATION')).toBe(true);
      expect(hasPermission('support_engineer', 'VIEW_TICKETS')).toBe(true);
      expect(hasPermission('support_engineer', 'UPDATE_TICKETS')).toBe(true);
      expect(hasPermission('support_engineer', 'VIEW_KNOWLEDGE')).toBe(true);
    });

    it('is denied privileged administrative and approval permissions', () => {
      expect(hasPermission('support_engineer', 'VIEW_APPROVALS')).toBe(false);
      expect(hasPermission('support_engineer', 'DECIDE_APPROVAL')).toBe(false);
      expect(hasPermission('support_engineer', 'EXECUTE_REMEDIATION')).toBe(false);
      expect(hasPermission('support_engineer', 'VIEW_AUDIT')).toBe(false);
      expect(hasPermission('support_engineer', 'MANAGE_SOURCES')).toBe(false);
      expect(hasPermission('support_engineer', 'MANAGE_RULES')).toBe(false);
      expect(hasPermission('support_engineer', 'EXECUTE_RETENTION')).toBe(false);
      expect(hasPermission('support_engineer', 'CHAOS_CONTROLS')).toBe(false);
    });

    it('route guards allow triage routes and block approvals, audit, and admin', () => {
      expect(canAccessRoute('support_engineer', '/')).toBe(true);
      expect(canAccessRoute('support_engineer', '/incidents')).toBe(true);
      expect(canAccessRoute('support_engineer', '/logs')).toBe(true);
      expect(canAccessRoute('support_engineer', '/upload')).toBe(true);
      expect(canAccessRoute('support_engineer', '/tickets')).toBe(true);
      expect(canAccessRoute('support_engineer', '/knowledge')).toBe(true);

      // Blocked routes
      expect(canAccessRoute('support_engineer', '/approvals')).toBe(false);
      expect(canAccessRoute('support_engineer', '/audit')).toBe(false);
      expect(canAccessRoute('support_engineer', '/admin')).toBe(false);
    });
  });

  describe('Approver Role (approver)', () => {
    it('has permission for review, decisions, execution, and audit', () => {
      expect(hasPermission('approver', 'VIEW_APPROVALS')).toBe(true);
      expect(hasPermission('approver', 'VIEW_APPROVALS_QUEUE')).toBe(true);
      expect(hasPermission('approver', 'DECIDE_APPROVAL')).toBe(true);
      expect(hasPermission('approver', 'APPROVE_REQUEST')).toBe(true);
      expect(hasPermission('approver', 'REJECT_REQUEST')).toBe(true);
      expect(hasPermission('approver', 'EXECUTE_REMEDIATION')).toBe(true);
      expect(hasPermission('approver', 'VIEW_AUDIT')).toBe(true);
    });

    it('is denied send approval requests, upload logs, system administration and chaos controls', () => {
      expect(hasPermission('approver', 'SEND_APPROVAL_REQUEST')).toBe(false);
      expect(hasPermission('approver', 'REQUEST_REMEDIATION')).toBe(false);
      expect(hasPermission('approver', 'UPLOAD_LOGS')).toBe(false);
      expect(hasPermission('approver', 'MANAGE_SOURCES')).toBe(false);
      expect(hasPermission('approver', 'MANAGE_RULES')).toBe(false);
      expect(hasPermission('approver', 'EXECUTE_RETENTION')).toBe(false);
      expect(hasPermission('approver', 'CHAOS_CONTROLS')).toBe(false);
      expect(hasPermission('approver', 'ADMIN_TICKET_OVERRIDE')).toBe(false);
    });

    it('route guards allow approvals and audit, block admin and upload', () => {
      expect(canAccessRoute('approver', '/approvals')).toBe(true);
      expect(canAccessRoute('approver', '/audit')).toBe(true);
      expect(canAccessRoute('approver', '/admin')).toBe(false);
      expect(canAccessRoute('approver', '/upload')).toBe(false);
    });
  });

  describe('Admin Role (admin)', () => {
    it('has administration, send approval request, and my-requests permissions', () => {
      expect(hasPermission('admin', 'SEND_APPROVAL_REQUEST')).toBe(true);
      expect(hasPermission('admin', 'VIEW_MY_REQUESTS')).toBe(true);
      expect(hasPermission('admin', 'VIEW_AUDIT')).toBe(true);
      expect(hasPermission('admin', 'MANAGE_SOURCES')).toBe(true);
      expect(hasPermission('admin', 'MANAGE_RULES')).toBe(true);
      expect(hasPermission('admin', 'EXECUTE_RETENTION')).toBe(true);
      expect(hasPermission('admin', 'CHAOS_CONTROLS')).toBe(true);
    });

    it('is denied approvals queue and approve/reject controls', () => {
      expect(hasPermission('admin', 'VIEW_APPROVALS')).toBe(false);
      expect(hasPermission('admin', 'VIEW_APPROVALS_QUEUE')).toBe(false);
      expect(hasPermission('admin', 'DECIDE_APPROVAL')).toBe(false);
      expect(hasPermission('admin', 'APPROVE_REQUEST')).toBe(false);
      expect(hasPermission('admin', 'REJECT_REQUEST')).toBe(false);
    });

    it('route guards allow admin routes but block approvals queue', () => {
      expect(canAccessRoute('admin', '/')).toBe(true);
      expect(canAccessRoute('admin', '/admin')).toBe(true);
      expect(canAccessRoute('admin', '/audit')).toBe(true);
      expect(canAccessRoute('admin', '/upload')).toBe(true);
      // Strictly blocked from Approvals Queue
      expect(canAccessRoute('admin', '/approvals')).toBe(false);
    });
  });

  describe('Role Display Names', () => {
    it('formats display names properly', () => {
      expect(getRoleDisplayName('admin')).toBe('System Administrator');
      expect(getRoleDisplayName('approver')).toBe('Senior Approver');
      expect(getRoleDisplayName('support_engineer')).toBe('Support Engineer (L1/L2)');
    });
  });
});
