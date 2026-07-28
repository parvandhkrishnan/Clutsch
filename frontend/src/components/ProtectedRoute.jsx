import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Loader2 } from 'lucide-react';

const ProtectedRoute = ({ children, adminOnly = false }) => {
  const { token, user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="loading-container">
        <Loader2 className="spin" size={48} />
        <p>Verifying authentication...</p>
      </div>
    );
  }

  if (!token) {
    // Redirect to login but save the current location they were trying to go to
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (adminOnly && user?.role !== 'admin') {
    // Not an admin — send them back to the main dashboard instead of
    // rendering the admin page shell. The backend independently enforces
    // this via get_admin_user (403 for non-admins); this is just so the
    // page doesn't render client-side for a role that can't use it.
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};

export default ProtectedRoute;
