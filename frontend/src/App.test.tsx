import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { Login } from './pages/Login';

describe('Frontend Smoke Tests', () => {
  it('renders login screen with presets and welcome title', () => {
    const handleLoginSuccess = () => {};
    render(<Login onLoginSuccess={handleLoginSuccess} />);
    expect(screen.getByText(/RootCause Copilot/i)).toBeDefined();
    expect(screen.getByRole('button', { name: /Sign In/i })).toBeDefined();
    expect(screen.getByRole('button', { name: /Admin/i })).toBeDefined();
    expect(screen.getByRole('button', { name: /Approver/i })).toBeDefined();
    expect(screen.getByRole('button', { name: /Support/i })).toBeDefined();
  });
});
