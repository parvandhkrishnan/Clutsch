import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Users,
  Settings,
  History,
  UserPlus,
  Search,
  X,
  Plus,
  Sliders,
  Lock,
  Globe,
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
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchMembers = async () => {
      try {
        const data = await api.get('/team/members');
        setUsers(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error("Failed to fetch team members:", err);
        setError(err.message || "Failed to load team members.");
      } finally {
        setLoading(false);
      }
    };
    fetchMembers();
  }, []);

  if (loading) return <div className="loading-state"><p>Loading team members...</p></div>;

  return (
    <div className="admin-content animate-in">
      <div className="section-header">
        <div>
          <h2>User Directory</h2>
          <p>Manage organization members and their access levels.</p>
        </div>
        <button
          className="btn btn-primary"
          disabled
          title="Invitations aren't available yet — there is no backend endpoint for sending invites."
        >
          <UserPlus size={18} />
          <span>Invite User</span>
        </button>
      </div>

      {error && <div className="error-state">{error}</div>}

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
              <option>User</option>
            </select>
          </div>
        </div>

        <table className="admin-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Availability</th>
              <th>Workload</th>
            </tr>
          </thead>
          <tbody>
            {users.map(user => (
              <tr key={user.id}>
                <td>
                  <div className="user-info-cell">
                    <div className="user-avatar-sm">{user.avatar || user.username?.slice(0, 2).toUpperCase()}</div>
                    <span className="user-name-bold">{user.username}</span>
                  </div>
                </td>
                <td>{user.email}</td>
                <td>
                  <span className={`role-badge ${(user.role || '').toLowerCase()}`}>{user.role}</span>
                </td>
                <td>
                  <span className={`status-pill ${(user.availability || '').toLowerCase()}`}>{user.availability}</span>
                </td>
                <td>{user.workload}</td>
              </tr>
            ))}
            {users.length === 0 && !error && (
              <tr>
                <td colSpan="5" style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                  No team members found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const PrioritizationRules = () => {
  const [contacts, setContacts] = useState({});
  const [projects, setProjects] = useState({});
  const [clients, setClients] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [showAddRuleModal, setShowAddRuleModal] = useState(false);
  const [newRule, setNewRule] = useState({ category: 'project', platform: 'gmail', handle: '', entityId: '', priority: 'medium' });

  useEffect(() => {
    const fetchRules = async () => {
      try {
        const [c, p, cl] = await Promise.all([
          api.get('/preferences/contacts'),
          api.get('/preferences/projects'),
          api.get('/preferences/clients'),
        ]);
        setContacts(c || {});
        setProjects(p || {});
        setClients(cl || {});
      } catch (err) {
        console.error("Failed to fetch prioritization rules:", err);
        setError(err.message || "Failed to load prioritization rules.");
      } finally {
        setLoading(false);
      }
    };
    fetchRules();
  }, []);

  // Flatten the three priority sources into a single list of "rules" for display.
  const rules = [];
  Object.entries(contacts).forEach(([platform, handles]) => {
    Object.entries(handles || {}).forEach(([handle, priority]) => {
      rules.push({ category: 'contact', key: `contact:${platform}:${handle}`, label: handle, sub: platform, priority });
    });
  });
  Object.entries(projects).forEach(([entityId, priority]) => {
    rules.push({ category: 'project', key: `project:${entityId}`, label: entityId, sub: 'Project', priority });
  });
  Object.entries(clients).forEach(([entityId, priority]) => {
    rules.push({ category: 'client', key: `client:${entityId}`, label: entityId, sub: 'Client', priority });
  });

  const savePriority = async (rule, newPriority) => {
    try {
      if (rule.category === 'contact') {
        await api.post('/preferences/contacts', { platform: rule.sub, handle: rule.label, priority: newPriority });
        setContacts(prev => ({ ...prev, [rule.sub]: { ...(prev[rule.sub] || {}), [rule.label]: newPriority } }));
      } else if (rule.category === 'project') {
        await api.post('/preferences/projects', { entity_id: rule.label, priority: newPriority });
        setProjects(prev => ({ ...prev, [rule.label]: newPriority }));
      } else if (rule.category === 'client') {
        await api.post('/preferences/clients', { entity_id: rule.label, priority: newPriority });
        setClients(prev => ({ ...prev, [rule.label]: newPriority }));
      }
    } catch (err) {
      console.error("Failed to update rule priority:", err);
    }
  };

  const deleteContactRule = async (platform, handle) => {
    try {
      await api.delete(`/preferences/contacts/${encodeURIComponent(platform)}/${encodeURIComponent(handle)}`);
      setContacts(prev => {
        const next = { ...prev };
        if (next[platform]) {
          const handles = { ...next[platform] };
          delete handles[handle];
          next[platform] = handles;
        }
        return next;
      });
    } catch (err) {
      console.error("Failed to delete rule:", err);
    }
  };

  const handleAddRule = async () => {
    try {
      if (newRule.category === 'contact') {
        const handle = newRule.handle.trim();
        if (!handle) return;
        await api.post('/preferences/contacts', { platform: newRule.platform, handle, priority: newRule.priority });
        setContacts(prev => ({ ...prev, [newRule.platform]: { ...(prev[newRule.platform] || {}), [handle]: newRule.priority } }));
      } else {
        const entityId = newRule.entityId.trim();
        if (!entityId) return;
        if (newRule.category === 'project') {
          await api.post('/preferences/projects', { entity_id: entityId, priority: newRule.priority });
          setProjects(prev => ({ ...prev, [entityId]: newRule.priority }));
        } else {
          await api.post('/preferences/clients', { entity_id: entityId, priority: newRule.priority });
          setClients(prev => ({ ...prev, [entityId]: newRule.priority }));
        }
      }
      setShowAddRuleModal(false);
      setNewRule({ category: 'project', platform: 'gmail', handle: '', entityId: '', priority: 'medium' });
    } catch (err) {
      console.error("Failed to create rule:", err);
    }
  };

  if (loading) return <div className="loading-state"><p>Loading Prioritization Rules...</p></div>;

  return (
    <div className="admin-content animate-in">
      <div className="section-header">
        <div>
          <h2>Prioritization Rules</h2>
          <p>Set fixed priority levels for specific contacts, projects, and clients.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowAddRuleModal(true)}>
          <Plus size={18} />
          <span>Add New Rule</span>
        </button>
      </div>

      <div className="rules-grid">
        <div className="card glass-effect weighting-card">
          <h3>Contact, Project & Client Priorities</h3>
          <p className="card-desc">Named entities that receive a fixed priority level in the scoring engine.</p>
          {error && <div className="error-state">{error}</div>}
          <div className="rules-list">
            {rules.map(rule => (
              <div key={rule.key} className="rule-item">
                <div className="rule-main">
                  <span className="rule-name">{rule.label}</span>
                  <span className="rule-type">{rule.category === 'contact' ? rule.sub : rule.sub}</span>
                </div>
                <div className="rule-interact">
                  <select
                    className="glass-select"
                    value={rule.priority}
                    onChange={(e) => savePriority(rule, e.target.value)}
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                  </select>
                  {rule.category === 'contact' && (
                    <button className="icon-btn text-red" title="Remove" onClick={() => deleteContactRule(rule.sub, rule.label)}>
                      <Trash2 size={16} />
                    </button>
                  )}
                </div>
              </div>
            ))}
            {rules.length === 0 && !error && (
              <p style={{ color: 'var(--text-muted)', padding: '20px 0' }}>No prioritization rules yet. Add one to get started.</p>
            )}
          </div>
        </div>

        <div className="card glass-effect global-settings">
          <h3>Global Engine Settings</h3>
          <p className="card-desc">
            Organization-wide mode toggles (aggressive prioritization, domain whitelisting, strict focus mode,
            AI reasoning transparency) are not yet implemented on the backend — coming soon.
          </p>
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
                <label>Rule Category</label>
                <select
                  className="glass-select full-width"
                  value={newRule.category}
                  onChange={(e) => setNewRule({ ...newRule, category: e.target.value })}
                >
                  <option value="project">Project</option>
                  <option value="client">Client</option>
                  <option value="contact">Contact / Stakeholder</option>
                </select>
              </div>

              {newRule.category === 'contact' ? (
                <>
                  <div className="form-group">
                    <label>Platform</label>
                    <select
                      className="glass-select full-width"
                      value={newRule.platform}
                      onChange={(e) => setNewRule({ ...newRule, platform: e.target.value })}
                    >
                      <option value="gmail">Gmail</option>
                      <option value="slack">Slack</option>
                      <option value="whatsapp">WhatsApp</option>
                      <option value="outlook">Outlook</option>
                      <option value="teams">Teams</option>
                      <option value="jira">Jira</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Contact Handle (email or username)</label>
                    <input
                      type="text" placeholder="e.g. boss@acme.com" className="glass-input"
                      value={newRule.handle}
                      onChange={(e) => setNewRule({ ...newRule, handle: e.target.value })}
                    />
                  </div>
                </>
              ) : (
                <div className="form-group">
                  <label>{newRule.category === 'project' ? 'Project Name / ID' : 'Client Name / ID'}</label>
                  <input
                    type="text" placeholder="e.g. Project Alpha" className="glass-input"
                    value={newRule.entityId}
                    onChange={(e) => setNewRule({ ...newRule, entityId: e.target.value })}
                  />
                </div>
              )}

              <div className="form-group">
                <label>Priority Level</label>
                <select
                  className="glass-select full-width"
                  value={newRule.priority}
                  onChange={(e) => setNewRule({ ...newRule, priority: e.target.value })}
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowAddRuleModal(false)}>Cancel</button>
              <button className="btn btn-primary" onClick={handleAddRule}>Create Rule</button>
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
          <h2>SSO / SAML Configuration</h2>
          <p>Secure organization-wide access with Enterprise identity providers.</p>
        </div>
      </div>

      <div className="card glass-effect sso-container">
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', padding: '60px 24px', gap: '16px', color: 'var(--text-muted)' }}>
          <Lock size={40} />
          <h3 style={{ margin: 0, color: 'var(--text-primary)' }}>Not Yet Implemented</h3>
          <p style={{ maxWidth: '480px' }}>
            SSO / SAML configuration isn't wired up on the backend yet — there is no way to save,
            test, or enforce an identity provider from Clutsch today. This tab is a placeholder for
            a planned feature and does not reflect any real configuration.
          </p>
        </div>
      </div>
    </div>
  );
};

const AuditLogs = () => {
  const [entries, setEntries] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchAudit = async () => {
      try {
        const data = await api.get('/dpdp/admin/audit');
        setEntries(data?.audit_entries || []);
        setStats(data?.stats || null);
      } catch (err) {
        console.error("Failed to fetch audit log:", err);
        if (err.status === 403) {
          setError("Admin access is required to view the compliance audit log.");
        } else {
          setError(err.message || "Failed to load audit log.");
        }
      } finally {
        setLoading(false);
      }
    };
    fetchAudit();
  }, []);

  if (loading) return <div className="loading-state"><p>Loading Audit Logs...</p></div>;

  return (
    <div className="admin-content animate-in">
      <div className="section-header">
        <div>
          <h2>Audit Logs</h2>
          <p>DPDP compliance audit trail — consent changes, grievances, and data-rights requests.</p>
        </div>
        <button
          className="btn btn-secondary"
          disabled
          title="Export isn't available yet — there is no export endpoint on the backend."
        >
          <History size={18} />
          <span>Export Logs</span>
        </button>
      </div>

      {error && <div className="error-state">{error}</div>}

      {!error && (
        <div className="card glass-effect directory-container">
          {stats && (
            <div className="table-controls">
              <span style={{ color: 'var(--text-muted)' }}>{stats.total_entries} total entries</span>
            </div>
          )}

          <table className="admin-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Regulation</th>
                <th>Request Type</th>
                <th>Outcome</th>
                <th>User Ref</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((log, idx) => (
                <tr key={idx}>
                  <td className="log-timestamp">{log.iso_timestamp}</td>
                  <td>{log.regulation}</td>
                  <td className="log-action-bold">{log.request_type}</td>
                  <td>
                    <span className={`status-pill ${(log.outcome || '').toLowerCase()}`}>{log.outcome}</span>
                  </td>
                  <td className="log-ip">{log.user_ref}</td>
                  <td className="log-target">{log.details || '-'}</td>
                </tr>
              ))}
              {entries.length === 0 && (
                <tr>
                  <td colSpan="6" style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                    No audit entries recorded yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

const OrgIntegrations = () => {
  return (
    <div className="admin-content animate-in">
      <div className="section-header">
        <div>
          <h2>Organization Integrations</h2>
          <p>Manage third-party connections at the organization level.</p>
        </div>
      </div>

      <div className="integrations-list-container admin-integrations card glass-effect">
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', padding: '60px 24px', gap: '16px', color: 'var(--text-muted)' }}>
          <Globe size={40} />
          <h3 style={{ margin: 0, color: 'var(--text-primary)' }}>Not Yet Implemented</h3>
          <p style={{ maxWidth: '520px' }}>
            There is no organization-level integration management backend yet. Members can connect
            their own accounts (Gmail, Slack, WhatsApp, Outlook, Teams, Jira) from the Integrations
            page, but a centralized, admin-managed view of org-wide connections isn't available today.
          </p>
        </div>
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
