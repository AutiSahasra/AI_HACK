import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { User } from './types';
import { getStoredUser, clearToken } from './api/client';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import {
  Login,
  Dashboard,
  UploadLogs,
  LogExplorer,
  Incidents,
  IncidentDetail,
  Tickets,
  Approvals,
  AuditLog,
  Knowledge,
  AdminSettings
} from './pages';

export const App: React.FC = () => {
  const [user, setUser] = useState<User | null>(getStoredUser());

  const handleLogout = () => {
    clearToken();
    setUser(null);
  };

  if (!user) {
    return <Login onLoginSuccess={setUser} />;
  }

  return (
    <BrowserRouter>
      <div className="app-container" style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <Navbar user={user} onLogout={handleLogout} />
        <div style={{ display: 'flex', flex: 1 }}>
          <Sidebar userRole={user.role} />
          <main className="main-content">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/upload" element={<UploadLogs />} />
              <Route path="/logs" element={<LogExplorer />} />
              <Route path="/incidents" element={<Incidents />} />
              <Route path="/incidents/:id" element={<IncidentDetail />} />
              <Route path="/tickets" element={<Tickets />} />
              <Route path="/approvals" element={<Approvals />} />
              <Route path="/audit" element={<AuditLog />} />
              <Route path="/knowledge" element={<Knowledge />} />
              <Route path="/admin" element={<AdminSettings />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
};
