import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Users, 
  Settings, 
  Shield, 
  History, 
  UserPlus, 
  Search, 
  MoreVertical,
  Check,
  X,
  Plus,
  Sliders,
  Lock,
  Globe,
  Database,
  Cpu,
  Zap,
  Target,
  Clock,
  Link,
  Activity,
  FileCode,
  ArrowRight,
  Save,
  Trash2
} from 'lucide-react';
import api from '../utils/api';
import { useEffect } from 'react';

const UserDirectory = () => {
  const [users, setUsers] = useState([
    { id: 1, name: 'Sarah Chen', email: 'sarah@acme.co', role: 'Admin', status: 'Active' },
    { id: 2, name: 'James Wilson', email: 'james@acme.co', role: 'Manager', status: 'Active' },
    { id: 3, name: 'Alex Rivera', email: 'alex@acme.co', role: 'Member', status: 'Active' },
    { id: 4, name: 'Maria Garcia', email: 'maria@acme.co', role: 'Member', status: 'Pending' },
    { id: 5, name: 'Tom Baker', email: 'tom@acme.co', role: 'Member', status: 'Inactive' },
  ]);

  const [showInviteModal, setShowInviteModal] = useState(false);

  return (
    <div className="admin-content animate-in">
      <div className="section-header">
        <div>
          <h2>User Directory</h2>
          <p>Manage organization members and their access levels.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowInviteModal(true)}>
          <UserPlus size={18} />
          <span>Invite User</span>
        </button>
      </div>

      <div className="card glass-effect directory-container">
        <div className="table-controls">
          <div className="search-bar">
            <Search size={18} />
            <input type="text" placeholder="Search users by name or email..." />
          </div>
          <div className="filter-group">
            <select className="glass-select">
              <option>All Roles</option>
              <option>Admin</option>
              <option>Manager</option>
              <option>Member</option>
            </select>
          </div>
        </div>

        <table className="admin-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {users.map(user => (
              <tr key={user.id}>
                <td>
                  <div className="user-info-cell">
                    <div className="user-avatar-sm">{user.name.split(' ').map(n => n[0]).join('')}</div>
                    <span className="user-name-bold">{user.name}</span>
                  </div>
                </td>
                <td>{user.email}</td>
                <td>
                  <span className={`role-badge ${user.role.toLowerCase()}`}>{user.role}</span>
                </td>
                <td>
                  <span className={`status-pill ${user.status.toLowerCase()}`}>{user.status}</span>
                </td>
                <td className="text-right">
                  <button className="icon-btn"><MoreVertical size={18} /></button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {showInviteModal && (
        <div className="modal-overlay">
          <div className="modal-card animate-in">
            <div className="modal-header">
              <h2>Invite New Member</h2>
              <button className="close-btn" onClick={() => setShowInviteModal(false)}><X size={20} /></button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>Email Address</label>
                <input type="email" placeholder="colleague@acme.co" className="glass-input" />
              </div>
              <div className="form-group">
                <label>Full Name (Optional)</label>
                <input type="text" placeholder="John Doe" className="glass-input" />
              </div>
              <div className="form-group">
                <label>Organization Role</label>
                <select className="glass-select full-width">
                  <option>Member</option>
                  <option>Manager</option>
                  <option>Admin</option>
                </select>
              </div>
              <div className="security-notice">
                <Shield size={16} />
                <span>Invited users will receive an email to set up their account and connect their data sources.</span>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowInviteModal(false)}>Cancel</button>
              <button className="btn btn-primary" onClick={() => setShowInviteModal(false)}>Send Invitation</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const PrioritizationRules = () => {
  const [rules, setRules] = useState([
    { id: 1, name: 'Project Alpha', type: 'Keyword', weight: 25, active: true },
    { id: 2, name: 'CEO/Executive', type: 'Stakeholder', weight: 40, active: true },
    { id: 3, name: 'Newsletter', type: 'Domain', weight: -15, active: true },
    { id: 4, name: 'Urgent Support', type: 'Subject', weight: 30, active: false },
  ]);

  const [showAddRuleModal, setShowAddRuleModal] = useState(false);

  const updateWeight = (id, newWeight) => {
    setRules(rules.map(r => r.id === id ? { ...r, weight: parseInt(newWeight) } : r));
  };

  return (
    <div className="admin-content animate-in">
      <div className="section-header">
        <div>
          <h2>Prioritization Rules</h2>
          <p>Define global weights to tune the AI prioritization engine for your team.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowAddRuleModal(true)}>
          <Plus size={18} />
          <span>Add New Rule</span>
        </button>
      </div>

      <div className="rules-grid">
        <div className="card glass-effect weighting-card">
          <h3>Keyword & Domain Weighting</h3>
          <p className="card-desc">Keywords, domains, and stakeholders that influence the Priority Score.</p>
          <div className="rules-list">
            {rules.map(rule => (
              <div key={rule.id} className="rule-item">
                <div className="rule-main">
                  <span className="rule-name">{rule.name}</span>
                  <span className="rule-type">{rule.type}</span>
                </div>
                <div className="rule-interact">
                  <div className="weight-control">
                    <span className={`weight-badge ${rule.weight > 0 ? 'positive' : 'negative'}`}>
                      {rule.weight > 0 ? `+${rule.weight}` : rule.weight}
                    </span>
                    <input 
                      type="range" 
                      min="-50" 
                      max="50" 
                      value={rule.weight} 
                      onChange={(e) => updateWeight(rule.id, e.target.value)}
                      className="weight-slider"
                    />
                  </div>
                  <label className="switch">
                    <input type="checkbox" checked={rule.active} onChange={() => {}} />
                    <span className="slider round"></span>
                  </label>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card glass-effect global-settings">
          <h3>Global Engine Settings</h3>
          <div className="engine-setting">
            <div className="setting-info">
              <label>Aggressive Prioritization</label>
              <p>Higher sensitivity to urgency signals.</p>
            </div>
            <label className="switch">
              <input type="checkbox" defaultChecked />
              <span className="slider round"></span>
            </label>
          </div>
          <div className="engine-setting">
            <div className="setting-info">
              <label>Domain Whitelisting</label>
              <p>Only prioritize communications from approved domains.</p>
            </div>
            <label className="switch">
              <input type="checkbox" />
              <span className="slider round"></span>
            </label>
          </div>
          <div className="engine-setting">
            <div className="setting-info">
              <label>Strict Focus Mode</label>
              <p>Auto-hide notifications for items with score &lt; 80.</p>
            </div>
            <label className="switch">
              <input type="checkbox" />
              <span className="slider round"></span>
            </label>
          </div>
          <div className="engine-setting">
            <div className="setting-info">
              <label>AI Reasoning Transparency</label>
              <p>Expose internal AI logic in user tooltips.</p>
            </div>
            <label className="switch">
              <input type="checkbox" defaultChecked />
              <span className="slider round"></span>
            </label>
          </div>
        </div>
      </div>

      {showAddRuleModal && (
        <div className="modal-overlay">
          <div className="modal-card animate-in">
            <div className="modal-header">
              <h2>Add Prioritization Rule</h2>
              <button className="close-btn" onClick={() => setShowAddRuleModal(false)}><X size={20} /></button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>Rule Target (Keyword, Email, or Domain)</label>
                <input type="text" placeholder="e.g. @stripe.com or 'Critical'" className="glass-input" />
              </div>
              <div className="form-group">
                <label>Rule Type</label>
                <select className="glass-select full-width">
                  <option>Keyword</option>
                  <option>Domain</option>
                  <option>Stakeholder</option>
                  <option>Subject line</option>
                </select>
              </div>
              <div className="form-group">
                <label>Priority Weighting</label>
                <div className="weight-input-container">
                  <input type="range" min="-100" max="100" defaultValue="20" className="weight-slider large" />
                  <div className="weight-labels">
                    <span>-100 (Ignore)</span>
                    <span>0 (Neutral)</span>
                    <span>+100 (Immediate)</span>
                  </div>
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowAddRuleModal(false)}>Cancel</button>
              <button className="btn btn-primary" onClick={() => setShowAddRuleModal(false)}>Create Rule</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const SSOConfig = () => {
  return (
    <div className="admin-content animate-in">
      <div className="section-header">
        <div>
          <h2>SSO & SAML Configuration</h2>
          <p>Secure organization-wide access with Enterprise identity providers.</p>
        </div>
      </div>

      <div className="card glass-effect sso-container">
        <div className="sso-status-banner active">
          <Globe size={24} />
          <div>
            <h4>Identity Federation Active</h4>
            <p>Your organization is currently authenticating via Okta SAML 2.0.</p>
          </div>
          <button className="btn-sm btn-secondary">Test Connection</button>
        </div>

        <div className="sso-grid">
          <div className="sso-form">
            <div className="form-group">
              <label><Lock size={16} /> Identity Provider Entity ID</label>
              <div className="input-with-copy">
                <input type="text" value="https://okta.com/exk1234567890" readOnly className="glass-input" />
              </div>
            </div>
            <div className="form-group">
              <label><Database size={16} /> SSO URL (ACS)</label>
              <div className="input-with-copy">
                <input type="text" value="https://api.clutsch.com/auth/sso/saml/acs" readOnly className="glass-input" />
              </div>
            </div>
            <div className="cert-section">
              <label>X.509 Public Certificate</label>
              <div className="cert-display">
                <code>-----BEGIN CERTIFICATE-----<br/>MIIDBTCCAe2gAwIBAgIQY7S9S...<br/>-----END CERTIFICATE-----</code>
                <button className="cert-copy-btn">Copy</button>
              </div>
            </div>
          </div>

          <div className="sso-sidebar-settings">
            <div className="card glass-effect inner-card">
              <h4>Security Enforcement</h4>
              <div className="setting-row">
                <span>Enforce SSO for all members</span>
                <label className="switch">
                  <input type="checkbox" defaultChecked />
                  <span className="slider round"></span>
                </label>
              </div>
              <div className="setting-row">
                <span>Auto-provision new users (JIT)</span>
                <label className="switch">
                  <input type="checkbox" />
                  <span className="slider round"></span>
                </label>
              </div>
              <div className="setting-row">
                <span>Allow password fallback (Admins)</span>
                <label className="switch">
                  <input type="checkbox" defaultChecked />
                  <span className="slider round"></span>
                </label>
              </div>
            </div>
            
            <div className="sso-help-box">
              <h5>Need help?</h5>
              <p>Check our <a href="/dashboard/help">SSO setup guide</a> for Okta, Azure AD, and Google Workspace.</p>
            </div>
          </div>
        </div>

        <div className="sso-footer">
          <button className="btn btn-secondary">Reset Configuration</button>
          <button className="btn btn-primary">Save Changes</button>
        </div>
      </div>
    </div>
  );
};

const AuditLogs = () => {
  const [logs] = useState([
    { id: 1, action: 'User Invited', actor: 'Sarah Chen', target: 'Maria Garcia', date: '2024-07-02 10:15:22', ip: '192.168.1.45' },
    { id: 2, action: 'SSO Updated', actor: 'Sarah Chen', target: 'Global Config', date: '2024-07-01 15:30:10', ip: '192.168.1.45' },
    { id: 3, action: 'Rule Created', actor: 'James Wilson', target: 'Project Alpha', date: '2024-07-01 09:44:05', ip: '10.0.4.12' },
    { id: 4, action: 'Role Changed', actor: 'Sarah Chen', target: 'Alex Rivera', date: '2024-06-30 18:22:12', ip: '192.168.1.45' },
    { id: 5, action: 'Org Integration', actor: 'James Wilson', target: 'Slack Enterprise', date: '2024-06-30 11:05:45', ip: '10.0.4.12' },
  ]);

  return (
    <div className="admin-content animate-in">
      <div className="section-header">
        <div>
          <h2>Audit Logs</h2>
          <p>Traceability and history of all administrative actions within the organization.</p>
        </div>
        <button className="btn btn-secondary">
          <History size={18} />
          <span>Export Logs</span>
        </button>
      </div>

      <div className="card glass-effect directory-container">
        <div className="table-controls">
          <div className="search-bar">
            <Search size={18} />
            <input type="text" placeholder="Filter logs by action, actor or target..." />
          </div>
          <div className="filter-group">
            <button className="btn-sm btn-secondary">Last 7 Days</button>
          </div>
        </div>

        <table className="admin-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Action</th>
              <th>Actor</th>
              <th>Target</th>
              <th>IP Address</th>
            </tr>
          </thead>
          <tbody>
            {logs.map(log => (
              <tr key={log.id}>
                <td className="log-timestamp">{log.date}</td>
                <td className="log-action-bold">{log.action}</td>
                <td>{log.actor}</td>
                <td className="log-target">{log.target}</td>
                <td className="log-ip">{log.ip}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const OrgIntegrations = () => {
  const [integrations] = useState([
    { id: 1, name: 'Slack Enterprise', type: 'Communication', status: 'Connected', scope: 'All Channels' },
    { id: 2, name: 'Google Workspace', type: 'Email/Auth', status: 'Connected', scope: 'Organization' },
    { id: 3, name: 'Jira Cloud', type: 'Productivity', status: 'Disconnected', scope: 'Engineering' },
    { id: 4, name: 'Zoom', type: 'Video', status: 'Connected', scope: 'All Members' },
  ]);

  return (
    <div className="admin-content animate-in">
      <div className="section-header">
        <div>
          <h2>Organization Integrations</h2>
          <p>Manage third-party connections at the organization level.</p>
        </div>
        <button className="btn btn-primary">
          <Plus size={18} />
          <span>Add Org Integration</span>
        </button>
      </div>

      <div className="integrations-list-container admin-integrations card glass-effect">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Integration</th>
              <th>Type</th>
              <th>Scope</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {integrations.map(integration => (
              <tr key={integration.id}>
                <td>
                  <div className="integration-name-cell">
                    <Globe size={18} className="text-primary" />
                    <span className="user-name-bold">{integration.name}</span>
                  </div>
                </td>
                <td>{integration.type}</td>
                <td>{integration.scope}</td>
                <td>
                  <span className={`status-pill ${integration.status.toLowerCase()}`}>{integration.status}</span>
                </td>
                <td className="text-right">
                  <button className="btn-sm btn-secondary">Configure</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const AITuning = () => {
  const [weights, setWeights] = useState({
    urgency: 0.3,
    importance: 0.3,
    sender_rank: 0.2,
    deadline: 0.2
  });

  const [semantics, setSemantics] = useState({
    financial_impact: 0.2,
    technical_debt: 0.15,
    customer_success: 0.2,
    compliance: 0.1
  });

  const [modes, setModes] = useState({
    deepWork: false,
    urgentTriage: false
  });

  const [loading, setLoading] = useState(true);

  // Fetch initial data
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [w, s] = await Promise.all([
          api.get('/preferences/weights'),
          api.get('/preferences/semantics')
        ]);
        if (w) setWeights(w);
        if (s) setSemantics(s);
      } catch (err) {
        console.error("Failed to fetch tuning data:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const saveWeights = async (newWeights) => {
    try {
      await api.post('/preferences/weights', newWeights);
    } catch (err) {
      console.error("Save weights failed:", err);
    }
  };

  const saveSemantics = async (newSemantics) => {
    try {
      await api.post('/preferences/semantics', { weights: newSemantics });
    } catch (err) {
      console.error("Save semantics failed:", err);
    }
  };

  const handleWeightChange = (key, value) => {
    const newWeights = { ...weights, [key]: parseFloat(value) };
    setWeights(newWeights);
    saveWeights(newWeights);
  };

  const handleSemanticChange = (key, value) => {
    const newSemantics = { ...semantics, [key]: parseFloat(value) };
    setSemantics(newSemantics);
    saveSemantics(newSemantics);
  };

  if (loading) return <div className="loading-state"><p>Loading Engine Preferences...</p></div>;

  return (
    <div className="admin-content animate-in">
      <div className="section-header">
        <div>
          <h2>Advanced AI Tuning</h2>
          <p>Fine-tune the prioritization engine's logic and sensitivity.</p>
        </div>
      </div>

      <div className="tuning-grid">
        <div className="card glass-effect tuning-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
            <Sliders size={20} className="text-primary" />
            <h3 style={{ margin: 0 }}>Global Priority Weights</h3>
          </div>
          <p className="card-desc">Adjust the baseline influence of core signals.</p>
          <div className="tuning-sliders">
            <div className="tuning-item">
              <div className="tuning-label">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Zap size={16} className="text-yellow" />
                  <span>Urgency</span>
                </div>
                <span className="weight-value">{(weights.urgency * 100).toFixed(0)}%</span>
              </div>
              <input 
                type="range" min="0" max="1" step="0.05" 
                value={weights.urgency} 
                onChange={(e) => handleWeightChange('urgency', e.target.value)} 
                className="weight-slider-full"
              />
            </div>
            <div className="tuning-item">
              <div className="tuning-label">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Target size={16} className="text-purple" />
                  <span>Importance</span>
                </div>
                <span className="weight-value">{(weights.importance * 100).toFixed(0)}%</span>
              </div>
              <input 
                type="range" min="0" max="1" step="0.05" 
                value={weights.importance} 
                onChange={(e) => handleWeightChange('importance', e.target.value)} 
                className="weight-slider-full"
              />
            </div>
            <div className="tuning-item">
              <div className="tuning-label">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Users size={16} className="text-blue" />
                  <span>Sender Rank</span>
                </div>
                <span className="weight-value">{(weights.sender_rank * 100).toFixed(0)}%</span>
              </div>
              <input 
                type="range" min="0" max="1" step="0.05" 
                value={weights.sender_rank} 
                onChange={(e) => handleWeightChange('sender_rank', e.target.value)} 
                className="weight-slider-full"
              />
            </div>
            <div className="tuning-item">
              <div className="tuning-label">
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Clock size={16} className="text-red" />
                  <span>Deadline Impact</span>
                </div>
                <span className="weight-value">{(weights.deadline * 100).toFixed(0)}%</span>
              </div>
              <input 
                type="range" min="0" max="1" step="0.05" 
                value={weights.deadline} 
                onChange={(e) => handleWeightChange('deadline', e.target.value)} 
                className="weight-slider-full"
              />
            </div>
          </div>
        </div>

        <div className="card glass-effect tuning-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
            <Cpu size={20} className="text-green" />
            <h3 style={{ margin: 0 }}>Semantic Topic Weighting</h3>
          </div>
          <p className="card-desc">Boost items containing specific semantic concepts.</p>
          <div className="tuning-sliders">
            {Object.entries(semantics).map(([key, value]) => (
              <div key={key} className="tuning-item">
                <div className="tuning-label">
                  <span>{key.replace('_', ' ').toUpperCase()}</span>
                  <span className="weight-value">+{value.toFixed(2)}</span>
                </div>
                <input 
                  type="range" min="0" max="0.5" step="0.05" 
                  value={value} 
                  onChange={(e) => handleSemanticChange(key, e.target.value)} 
                  className="weight-slider-full"
                />
              </div>
            ))}
          </div>
        </div>

        <div className="card glass-effect tuning-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
            <Globe size={20} className="text-blue" />
            <h3 style={{ margin: 0 }}>Contextual Scaling Modes</h3>
          </div>
          <p className="card-desc">Override engine behavior for specific workflows.</p>
          <div className="mode-toggles">
            <div className="engine-setting">
              <div className="setting-info">
                <label>Deep Work Mode</label>
                <p>Aggressively deprioritize non-critical communications to protect focus.</p>
              </div>
              <label className="switch">
                <input 
                  type="checkbox" 
                  checked={modes.deepWork} 
                  onChange={(e) => setModes({...modes, deepWork: e.target.checked})} 
                />
                <span className="slider round"></span>
              </label>
            </div>
            <div className="engine-setting">
              <div className="setting-info">
                <label>Urgent Triage Mode</label>
                <p>Maximum sensitivity to urgency signals. Ideal for incident management.</p>
              </div>
              <label className="switch">
                <input 
                  type="checkbox" 
                  checked={modes.urgentTriage} 
                  onChange={(e) => setModes({...modes, urgentTriage: e.target.checked})} 
                />
                <span className="slider round"></span>
              </label>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

const CustomConnectors = () => {
  const [connectors, setConnectors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingConnector, setEditingConnector] = useState(null);

  const [formData, setFormData] = useState({
    name: '',
    url: '',
    method: 'GET',
    auth_type: 'none',
    auth_header: 'Authorization',
    auth_value: '',
    polling_interval: 60,
    mapping: {
      id: 'id',
      text: 'title',
      source: 'source',
      sender: 'author',
      deadline: 'due_date'
    },
    urgency_triggers: []
  });

  const fetchConnectors = async () => {
    try {
      const data = await api.get('/integrations/custom');
      setConnectors(data);
    } catch (err) {
      console.error("Failed to fetch connectors:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConnectors();
  }, []);

  const handleSave = async () => {
    try {
      if (editingConnector) {
        await api.patch(`/integrations/custom/${editingConnector.id}`, formData);
      } else {
        await api.post('/integrations/custom', formData);
      }
      setShowModal(false);
      setEditingConnector(null);
      fetchConnectors();
    } catch (err) {
      console.error("Save failed:", err);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to delete this connector?")) return;
    try {
      await api.delete(`/integrations/custom/${id}`);
      fetchConnectors();
    } catch (err) {
      console.error("Delete failed:", err);
    }
  };

  const openModal = (connector = null) => {
    if (connector) {
      setEditingConnector(connector);
      setFormData(connector);
    } else {
      setEditingConnector(null);
      setFormData({
        name: '',
        url: '',
        method: 'GET',
        auth_type: 'none',
        auth_header: 'Authorization',
        auth_value: '',
        polling_interval: 60,
        mapping: { id: 'id', text: 'title', source: 'source', sender: 'author', deadline: 'due_date' },
        urgency_triggers: []
      });
    }
    setShowModal(true);
  };

  if (loading) return <div className="loading-state"><p>Loading Custom Connectors...</p></div>;

  return (
    <div className="admin-content animate-in">
      <div className="section-header">
        <div>
          <h2>Custom Integration Framework</h2>
          <p>Build and manage proprietary third-party connectors.</p>
        </div>
        <button className="btn btn-primary" onClick={() => openModal()}>
          <Plus size={18} />
          <span>Register New Connector</span>
        </button>
      </div>

      <div className="card glass-effect directory-container">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Connector Name</th>
              <th>Endpoint URL</th>
              <th>Auth Method</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {connectors.map(c => (
              <tr key={c.id}>
                <td>
                  <div className="integration-name-cell">
                    <Link size={18} className="text-primary" />
                    <span className="user-name-bold">{c.name}</span>
                  </div>
                </td>
                <td style={{ maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {c.url}
                </td>
                <td><span className="role-badge member">{c.auth_type.toUpperCase()}</span></td>
                <td>
                  <label className="switch">
                    <input 
                      type="checkbox" 
                      checked={c.enabled} 
                      onChange={async (e) => {
                        try {
                          await api.patch(`/integrations/custom/${c.id}`, { enabled: e.target.checked });
                          fetchConnectors();
                        } catch (err) {
                          console.error("Toggle failed:", err);
                        }
                      }} 
                    />
                    <span className="slider round"></span>
                  </label>
                </td>
                <td className="text-right">
                  <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                    <button className="btn-sm btn-secondary" onClick={() => openModal(c)}>Configure</button>
                    <button className="icon-btn text-red" onClick={() => handleDelete(c.id)}><Trash2 size={16} /></button>
                  </div>
                </td>
              </tr>
            ))}
            {connectors.length === 0 && (
              <tr>
                <td colSpan="5" style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                  No custom connectors registered yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {showModal && (
        <div className="modal-overlay">
          <div className="modal-card animate-in" style={{ maxWidth: '800px', width: '90%' }}>
            <div className="modal-header">
              <h2>{editingConnector ? 'Configure' : 'Register'} Custom Connector</h2>
              <button className="close-btn" onClick={() => setShowModal(false)}><X size={20} /></button>
            </div>
            <div className="modal-body">
              <div className="admin-tabs" style={{ marginBottom: '20px' }}>
                <button className="admin-tab-btn active"><Settings size={16} /> Basic Config</button>
              </div>

              <div className="form-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                <div className="form-group">
                  <label>Connector Name</label>
                  <input 
                    type="text" className="glass-input" 
                    value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})}
                  />
                </div>
                <div className="form-group">
                  <label>Endpoint URL</label>
                  <input 
                    type="text" className="glass-input" 
                    value={formData.url} onChange={e => setFormData({...formData, url: e.target.value})}
                  />
                </div>
                <div className="form-group">
                  <label>Auth Type</label>
                  <select 
                    className="glass-select full-width"
                    value={formData.auth_type} onChange={e => setFormData({...formData, auth_type: e.target.value})}
                  >
                    <option value="none">None</option>
                    <option value="api_key">API Key</option>
                    <option value="bearer">Bearer Token</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Polling Interval (Minutes)</label>
                  <input 
                    type="number" className="glass-input" 
                    value={formData.polling_interval} onChange={e => setFormData({...formData, polling_interval: parseInt(e.target.value)})}
                  />
                </div>
              </div>

              <div style={{ marginTop: '24px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
                  <FileCode size={20} className="text-purple" />
                  <h3 style={{ margin: 0 }}>Data Mapping Normalizer</h3>
                </div>
                <p className="card-desc">Map JSON response keys to Clutsch schema fields.</p>
                <div className="mapping-grid" style={{ background: 'rgba(0,0,0,0.02)', padding: '16px', borderRadius: '12px', border: '1px solid var(--glass-border)' }}>
                  {Object.entries(formData.mapping).map(([target, source]) => (
                    <div key={target} style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
                      <div style={{ flex: 1, fontWeight: 600, color: 'var(--text-muted)' }}>{target.toUpperCase()}</div>
                      <ArrowRight size={16} />
                      <input 
                        type="text" className="glass-input" style={{ flex: 2 }}
                        value={source} 
                        onChange={e => {
                          const newMapping = {...formData.mapping, [target]: e.target.value};
                          setFormData({...formData, mapping: newMapping});
                        }}
                      />
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ marginTop: '24px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
                  <Activity size={20} className="text-yellow" />
                  <h3 style={{ margin: 0 }}>Urgency Triggers</h3>
                </div>
                <button className="btn-sm btn-secondary" onClick={() => setFormData({...formData, urgency_triggers: [...formData.urgency_triggers, { field: '', value: '', boost: 0.1 }]})}>
                  <Plus size={14} /> Add Trigger
                </button>
                <div style={{ marginTop: '12px' }}>
                  {formData.urgency_triggers.map((trigger, idx) => (
                    <div key={idx} style={{ display: 'flex', gap: '10px', marginBottom: '8px' }}>
                      <input placeholder="Field" className="glass-input" value={trigger.field} onChange={e => {
                        const newTriggers = [...formData.urgency_triggers];
                        newTriggers[idx].field = e.target.value;
                        setFormData({...formData, urgency_triggers: newTriggers});
                      }} />
                      <input placeholder="Value" className="glass-input" value={trigger.value} onChange={e => {
                        const newTriggers = [...formData.urgency_triggers];
                        newTriggers[idx].value = e.target.value;
                        setFormData({...formData, urgency_triggers: newTriggers});
                      }} />
                      <input type="number" step="0.05" className="glass-input" style={{ width: '80px' }} value={trigger.boost} onChange={e => {
                        const newTriggers = [...formData.urgency_triggers];
                        newTriggers[idx].boost = parseFloat(e.target.value);
                        setFormData({...formData, urgency_triggers: newTriggers});
                      }} />
                    </div>
                  ))}
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowModal(false)}>Cancel</button>
              <button className="btn btn-primary" onClick={handleSave}><Save size={18} /> Save Connector</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const Admin = () => {
  const { tab = 'users' } = useParams();
  const navigate = useNavigate();

  const tabs = [
    { id: 'users', label: 'User Directory', icon: Users },
    { id: 'integrations', label: 'Org Integrations', icon: Globe },
    { id: 'custom', label: 'Custom Connectors', icon: Link },
    { id: 'rules', label: 'Priority Rules', icon: Sliders },
    { id: 'tuning', label: 'Advanced Tuning', icon: Cpu },
    { id: 'sso', label: 'SSO / Security', icon: Lock },
    { id: 'logs', label: 'Audit Logs', icon: History },
  ];

  return (
    <div className="admin-page">
      <header className="page-header">
        <h1>Enterprise Administration</h1>
        <p>Organization-level governance and configuration.</p>
      </header>

      <div className="admin-tabs">
        {tabs.map(t => (
          <button 
            key={t.id}
            className={`admin-tab-btn ${tab === t.id ? 'active' : ''}`}
            onClick={() => navigate(`/dashboard/admin/${t.id}`)}
          >
            <t.icon size={18} />
            <span>{t.label}</span>
          </button>
        ))}
      </div>

      <div className="admin-body">
        {tab === 'users' && <UserDirectory />}
        {tab === 'integrations' && <OrgIntegrations />}
        {tab === 'custom' && <CustomConnectors />}
        {tab === 'rules' && <PrioritizationRules />}
        {tab === 'tuning' && <AITuning />}
        {tab === 'sso' && <SSOConfig />}
        {tab === 'logs' && <AuditLogs />}
      </div>
    </div>
  );
};

export default Admin;
