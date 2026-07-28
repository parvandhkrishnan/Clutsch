import React from 'react';
import { HashRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Sidebar from './components/Sidebar';
import CookieConsent from './components/CookieConsent';
import ErrorBanner from './components/ErrorBanner';
import Dashboard from './pages/Dashboard';
import Integrations from './pages/Integrations';
import Settings from './pages/Settings';
import Tasks from './pages/Tasks';
import Login from './pages/Login';
import SSOPopup from './pages/SSOPopup';
import LandingPage from './pages/LandingPage';
import Onboarding from './pages/Onboarding';
import Analytics from './pages/Analytics';
import Billing from './pages/Billing';
import HelpCenter from './pages/HelpCenter';
import Admin from './pages/Admin';
import './App.css';

const MainLayout = ({ children }) => (
  <div className="app-container">
    <a href="#main-content" className="skip-to-content" style={{
      position: 'absolute', left: '-9999px', zIndex: 9999,
      padding: '8px 16px', background: 'var(--primary-blue)', color: 'white',
      textDecoration: 'none', borderRadius: '0 0 4px 4px', fontSize: '0.9rem'
    }}
    onFocus={(e) => e.target.style.left = '8px'}
    onBlur={(e) => e.target.style.left = '-9999px'}>
      Skip to content
    </a>
    <Sidebar />
    <main className="main-content" id="main-content">
      {children}
    </main>
  </div>
);

function App() {
  return (
    <AuthProvider>
      <Router>
        <ErrorBanner />
        <CookieConsent />
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<Login />} />
          <Route path="/sso-popup" element={<SSOPopup />} />
          <Route path="/onboarding" element={
            <ProtectedRoute>
              <Onboarding />
            </ProtectedRoute>
          } />
          
          {/* Protected Routes */}
          <Route path="/dashboard" element={
            <ProtectedRoute>
              <MainLayout><Dashboard /></MainLayout>
            </ProtectedRoute>
          } />
          
          <Route path="/integrations" element={
            <ProtectedRoute>
              <MainLayout><Integrations /></MainLayout>
            </ProtectedRoute>
          } />
          
          <Route path="/settings" element={
            <ProtectedRoute>
              <MainLayout><Settings /></MainLayout>
            </ProtectedRoute>
          } />

          <Route path="/tasks" element={
            <ProtectedRoute>
              <MainLayout><Tasks /></MainLayout>
            </ProtectedRoute>
          } />

          <Route path="/dashboard/analytics" element={
            <ProtectedRoute>
              <MainLayout><Analytics /></MainLayout>
            </ProtectedRoute>
          } />

          <Route path="/dashboard/billing" element={
            <ProtectedRoute>
              <MainLayout><Billing /></MainLayout>
            </ProtectedRoute>
          } />

          <Route path="/dashboard/help" element={
            <ProtectedRoute>
              <MainLayout><HelpCenter /></MainLayout>
            </ProtectedRoute>
          } />

          <Route path="/dashboard/admin" element={
            <ProtectedRoute adminOnly>
              <MainLayout><Admin /></MainLayout>
            </ProtectedRoute>
          } />

          <Route path="/dashboard/admin/:tab" element={
            <ProtectedRoute adminOnly>
              <MainLayout><Admin /></MainLayout>
            </ProtectedRoute>
          } />
          
          <Route path="/projects" element={
            <ProtectedRoute>
              <MainLayout><div className="card"><h2>Projects Page</h2><p>Coming soon...</p></div></MainLayout>
            </ProtectedRoute>
          } />
          
          <Route path="/messages" element={
            <ProtectedRoute>
              <MainLayout><div className="card"><h2>Messages Page</h2><p>Coming soon...</p></div></MainLayout>
            </ProtectedRoute>
          } />

          {/* Redirect all other routes to landing or login */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;
