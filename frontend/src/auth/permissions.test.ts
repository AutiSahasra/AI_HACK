import { describe, it, expect } from 'vitest';
import { hasPermission, canAccessRoute, getRoleDisplayName } from './permissions';

describe('Role-Based Access Control (RBAC) System - 2 Roles (Support & Approver)', () => {
  describe('Support Engineer Role (support_engineer)', () => {
    it('has permission for incident triage and log exploration', () => {
      expect(hasPermission('support_engineer', 'VIEW_DASHBOARD')).toBe(true);
      expect(hasPermission('support_engineer', 'UPLOAD_LOGS')).toBe(true);
      expect(hasPermission('support_engineer', 'VIEW_LOGS')).toBe(true);
      expect(hasPermission('support_engineer', 'VIEW_INCIDENTS')).toBe(true);
      expect(hasPermission('support_engineer', 'REQUEST_REMEDIATION')).toBe(true);
      expect(hasPermission('support_engineer', 'SEND_APPROVAL_REQUEST')).toBe(true);
      expect(hasPermission('support_engineer', 'VIEW_MY_REQUESTS')).toBe(true);
    });

    it('is denied approvals decisions and queue access', () => {
      expect(hasPermission('support_engineer', 'VIEW_APPROVALS')).toBe(false);
      expect(hasPermission('support_engineer', 'VIEW_APPROVALS_QUEUE')).toBe(false);
      expect(hasPermission('support_engineer', 'DECIDE_APPROVAL')).toBe(false);
      expect(hasPermission('support_engineer', 'EXECUTE_REMEDIATION')).toBe(false);
      expect(hasPermission('support_engineer', 'CHAOS_CONTROLS')).toBe(false);
    });

    it('route guards allow only dashboard, incidents, logs, and upload; blocks approvals and removed routes', () => {
      expect(canAccessRoute('support_engineer', '/')).toBe(true);
      expect(canAccessRoute('support_engineer', '/incidents')).toBe(true);
      expect(canAccessRoute('support_engineer', '/logs')).toBe(true);
      expect(canAccessRoute('support_engineer', '/upload')).toBe(true);

      // Blocked / removed routes
      expect(canAccessRoute('support_engineer', '/approvals')).toBe(false);
      expect(canAccessRoute('support_engineer', '/tickets')).toBe(false);
      expect(canAccessRoute('support_engineer', '/knowledge')).toBe(false);
      expect(canAccessRoute('support_engineer', '/audit')).toBe(false);
      expect(canAccessRoute('support_engineer', '/admin')).toBe(false);
    });
  });

  describe('Approver Role (approver)', () => {
    it('has permission for review, decisions, execution, and chaos controls', () => {
      expect(hasPermission('approver', 'VIEW_APPROVALS')).toBe(true);
      expect(hasPermission('approver', 'VIEW_APPROVALS_QUEUE')).toBe(true);
      expect(hasPermission('approver', 'DECIDE_APPROVAL')).toBe(true);
      expect(hasPermission('approver', 'APPROVE_REQUEST')).toBe(true);
      expect(hasPermission('approver', 'REJECT_REQUEST')).toBe(true);
      expect(hasPermission('approver', 'EXECUTE_REMEDIATION')).toBe(true);
      expect(hasPermission('approver', 'CHAOS_CONTROLS')).toBe(true);
    });

    it('is denied send approval requests and upload logs', () => {
      expect(hasPermission('approver', 'SEND_APPROVAL_REQUEST')).toBe(false);
      expect(hasPermission('approver', 'UPLOAD_LOGS')).toBe(false);
    });

    it('route guards allow dashboard, incidents, logs, and approvals; blocks upload and removed routes', () => {
      expect(canAccessRoute('approver', '/')).toBe(true);
      expect(canAccessRoute('approver', '/incidents')).toBe(true);
      expect(canAccessRoute('approver', '/logs')).toBe(true);
      expect(canAccessRoute('approver', '/approvals')).toBe(true);

      // Blocked / removed routes
      expect(canAccessRoute('approver', '/upload')).toBe(false);
      expect(canAccessRoute('approver', '/tickets')).toBe(false);
      expect(canAccessRoute('approver', '/knowledge')).toBe(false);
      expect(canAccessRoute('approver', '/audit')).toBe(false);
      expect(canAccessRoute('approver', '/admin')).toBe(false);
    });
  });

  describe('Role Display Names', () => {
    it('formats display names properly for 2 active roles', () => {
      expect(getRoleDisplayName('approver')).toBe('Senior Approver');
      expect(getRoleDisplayName('support_engineer')).toBe('Support Engineer (L1/L2)');
    });
  });
});
