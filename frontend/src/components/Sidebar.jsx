import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import LegalModal from './LegalModal';
import { 
  LayoutDashboard, 
  CheckSquare, 
  Folder, 
  MessageSquare, 
  Share2,
  Settings,
  LogOut,
  Shield,
  FileText,
  BarChart3,
  CreditCard,
  HelpCircle,
  ShieldAlert
} from 'lucide-react';

const API_BASE_URL = '';

const SidebarItem = ({ icon: Icon, label, to, badge, onClick }) => {
  if (onClick) {
    return (
      <button className="sidebar-item" onClick={onClick}>
        <Icon size={20} />
        <span>{label}</span>
      </button>
    );
  }
  return (
    <NavLink 
      to={to} 
      className={({ isActive }) => `sidebar-item ${isActive ? 'active' : ''}`}
    >
      <Icon size={20} />
      <span>{label}</span>
      {badge > 0 && <span className="badge">{badge}</span>}
    </NavLink>
  );
};

const Sidebar = () => {
  const { token, logout } = useAuth();
  const [stats, setStats] = useState({ snoozed_count: 0 });
  const [legalModal, setLegalModal] = useState(null); // 'tos' | 'privacy' | null

  useEffect(() => {
    if (!token) return;

    const fetchStats = async () => {
      try {
        const data = await api.get('/stats');
        setStats(data);
      } catch (err) {
        console.error("Failed to fetch stats:", err);
      }
    };

    fetchStats();
    // Poll for stats updates
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, [token]);

  return (
    <aside className="sidebar">
      <div className="logo">
        <div className="logo-icon" style={{ background: 'linear-gradient(135deg, #6C3BFF, #00F0FF)' }}>C</div>
        <span className="logo-text text-display" style={{ fontWeight: 700, letterSpacing: '-0.03em' }}>Clutsch</span>
      </div>
      <nav className="nav-links">
        <SidebarItem icon={LayoutDashboard} label="Dashboard" to="/dashboard" />
        <SidebarItem 
          icon={CheckSquare} 
          label="Tasks" 
          to="/tasks" 
          badge={stats.snoozed_count} 
        />
        <SidebarItem icon={BarChart3} label="Analytics" to="/dashboard/analytics" />
        <SidebarItem icon={ShieldAlert} label="Admin" to="/dashboard/admin" />
        {/* <SidebarItem icon={Folder} label="Projects" to="/projects" /> */}
        {/* <SidebarItem icon={MessageSquare} label="Messages" to="/messages" /> */}
        <SidebarItem icon={Share2} label="Integrations" to="/integrations" />
        <SidebarItem icon={CreditCard} label="Billing" to="/dashboard/billing" />
        <SidebarItem icon={Settings} label="Settings" to="/settings" />
        <SidebarItem icon={HelpCircle} label="Help Center" to="/dashboard/help" />
      </nav>

      <div className="sidebar-footer">
        <SidebarItem 
          icon={FileText} 
          label="Terms of Service" 
          onClick={() => setLegalModal('tos')} 
        />
        <SidebarItem 
          icon={Shield} 
          label="Privacy Policy" 
          onClick={() => setLegalModal('privacy')} 
        />
        <button className="sidebar-item logout-btn" onClick={logout}>
          <LogOut size={20} />
          <span>Logout</span>
        </button>
      </div>

      {legalModal && (
        <LegalModal 
          type={legalModal} 
          onClose={() => setLegalModal(null)} 
        />
      )}
    </aside>
  );
};

export default Sidebar;
