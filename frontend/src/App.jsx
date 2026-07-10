import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
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
import LandingPage from './pages/LandingPage';
import Onboarding from './pages/Onboarding';
import Analytics from './pages/Analytics';
import Billing from './pages/Billing';
import HelpCenter from './pages/HelpCenter';
import Admin from './pages/Admin';
import './App.css';

const MainLayout = ({ children }) => (
  <div className="app-container">
    <a href="#main-content" className="skip-to-content">Skip to content</a>
    <Sidebar />
    <main id="main-content" className="main-content" tabIndex={-1}>
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
            <ProtectedRoute>
              <MainLayout><Admin /></MainLayout>
            </ProtectedRoute>
          } />

          <Route path="/dashboard/admin/:tab" element={
            <ProtectedRoute>
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
