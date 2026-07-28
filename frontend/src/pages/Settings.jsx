import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import { 
  User, 
  Bell, 
  Shield, 
  Lock, 
  Trash2, 
  Mail, 
  MessageCircle, 
  Plus, 
  X, 
  Loader2,
  LayoutGrid
} from 'lucide-react';
import { showToast } from '../utils/toast';

const API_BASE_URL = '';

const Settings = () => {
  const { token } = useAuth();
  const [priorities, setPriorities] = useState({});
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [showNominateModal, setShowNominateModal] = useState(false);
  const [showGrievanceModal, setShowGrievanceModal] = useState(false);
  const [newContact, setNewContact] = useState({ platform: 'gmail', handle: '', priority: 'high' });
  const [nominee, setNominee] = useState({ name: '', email: '', relationship: '' });
  const [grievance, setGrievance] = useState({ subject: 'Data Access', description: '' });
  const [exportStatus, setExportStatus] = useState('');
  // Granular per-purpose consent: { purpose_id: { title, description, required_for_service, enabled } }
  const [consentPrefs, setConsentPrefs] = useState({});
  const [consentLoadingPurpose, setConsentLoadingPurpose] = useState(null);
  const [consentStatus, setConsentStatus] = useState('');

  const fetchConsentStatus = useCallback(async () => {
    try {
      const data = await api.get('/dpdp/consent');
      setConsentPrefs(data.consent_purposes || {});
    } catch (err) {
      // Silently fail — non-critical consent fetch
    }
  }, []);

  const handleConsentChange = async (purposeId, newValue) => {
    if (!newValue) {
      const meta = consentPrefs[purposeId];
      const confirmed = window.confirm(
        `Disabling "${meta?.title || purposeId}" may affect related features for your account. Are you sure you want to withdraw this consent?`
      );
      if (!confirmed) return;
    }

    setConsentLoadingPurpose(purposeId);
    setConsentStatus('');
    try {
      const data = await api.post('/dpdp/consent', { [purposeId]: newValue });
      // Merge the updated values back into each purpose's metadata (the
      // response only returns { purpose_id: bool }, not full metadata).
      setConsentPrefs(prev => {
        const next = { ...prev };
        for (const [id, enabled] of Object.entries(data.current_preferences || {})) {
          next[id] = { ...(next[id] || {}), enabled };
        }
        return next;
      });
      setConsentStatus(newValue ? 'Consent granted' : 'Consent withdrawn');
      setTimeout(() => setConsentStatus(''), 3000);
    } catch (err) {
      setConsentStatus('Update failed');
      setTimeout(() => setConsentStatus(''), 3000);
    } finally {
      setConsentLoadingPurpose(null);
    }
  };

  const handleNominate = async () => {
    try {
      await api.post('/dpdp/nominate', nominee);
      setShowNominateModal(false);
      showToast("Nominee registered successfully.", "success");
    } catch (err) {
      showToast("Failed to register nominee.", "error");
    }
  };

  const handleGrievance = async () => {
    try {
      await api.post('/dpdp/grievance', grievance);
      setShowGrievanceModal(false);
      setGrievance({ subject: 'Data Access', description: '' });
      showToast("Grievance logged. We will respond within 7 days.", "success");
    } catch (err) {
      showToast("Failed to log grievance.", "error");
    }
  };

  const handleExport = async () => {
    try {
      const data = await api.get('/privacy/export');
      // Create a blob and download it
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Clutsch-export-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setExportStatus('Export started!');
      setTimeout(() => setExportStatus(''), 5000);
    } catch (err) {
      setExportStatus('Export failed. Please try again.');
    }
  };

  const handleDeleteAccount = async () => {
    if (window.confirm("ARE YOU ABSOLUTELY SURE? This will permanently delete your account and all associated data. This action cannot be undone.")) {
      try {
        await api.delete('/privacy/account');
        showToast("Account deleted successfully.", "success");
        // Logout will happen automatically if api utility handles 401 on next request,
        // but let's be explicit.
        localStorage.clear();
        window.location.href = '/login';
      } catch (err) {
        showToast("Failed to delete account. Please contact support.", "error");
      }
    }
  };

  const fetchPriorities = useCallback(async () => {
    try {
      const data = await api.get('/preferences/contacts');
      setPriorities(data);
    } catch (err) {
      // Fallback to mock if API not ready
      if (err.status === 404) {
        setPriorities({
          gmail: { 'boss@company.com': 'high' },
          slack: { 'u123': 'high', 'u456': 'medium' }
        });
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPriorities();
    fetchConsentStatus();
  }, [fetchPriorities, fetchConsentStatus]);

  const handleAdd = async () => {
    try {
      await api.post('/preferences/contacts', newContact);
      setShowAddModal(false);
      setNewContact({ platform: 'gmail', handle: '', priority: 'high' });
      fetchPriorities();
    } catch (err) {
      // Mock update for demonstration
      const platform = newContact.platform;
      setPriorities(prev => ({
        ...prev,
        [platform]: {
          ...(prev[platform] || {}),
          [newContact.handle]: newContact.priority
        }
      }));
      setShowAddModal(false);
    }
  };

  const handleDelete = async (platform, handle) => {
    try {
      await api.delete(`/preferences/contacts/${platform}/${handle}`);
      fetchPriorities();
    } catch (err) {
      // Mock update
      setPriorities(prev => {
        const updated = { ...prev };
        if (updated[platform]) {
          delete updated[platform][handle];
        }
        return updated;
      });
    }
  };

  const getPlatformIcon = (platform) => {
    switch (platform.toLowerCase()) {
      case 'slack': return MessageCircle;
      case 'gmail':
      case 'outlook': return Mail;
      case 'jira': return LayoutGrid;
      default: return MessageCircle;
    }
  };

  return (
    <div className="settings-page">
      <header className="page-header">
        <h1>Settings</h1>
        <p>Manage your account preferences and contact priorities.</p>
      </header>

      <div className="settings-grid">
        <aside className="settings-nav card">
          <nav>
            <a href="#profile" className="settings-nav-item">
              <User size={18} />
              <span>Profile</span>
            </a>
            <a href="#priorities" className="settings-nav-item active">
              <Bell size={18} />
              <span>Contact Priorities</span>
            </a>
            <a href="#privacy" className="settings-nav-item">
              <Shield size={18} />
              <span>Privacy & Compliance</span>
            </a>
            <a href="#security" className="settings-nav-item">
              <Lock size={18} />
              <span>Security</span>
            </a>
          </nav>
        </aside>

        <main className="settings-content">
          <section id="priorities" className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h2>Contact Priorities</h2>
              <button className="btn btn-primary" onClick={() => setShowAddModal(true)}>
                <Plus size={18} />
                <span>Add Contact</span>
              </button>
            </div>
            <p className="section-desc">
              Manually set priority levels for specific contacts. These will override AI analysis.
            </p>
            
            <div className="contact-priorities-list">
              {loading ? (
                <div style={{ textAlign: 'center', padding: '40px' }}><Loader2 className="spin" /></div>
              ) : Object.keys(priorities).length > 0 ? (
                Object.entries(priorities).flatMap(([platform, handles]) => 
                  Object.entries(handles).map(([handle, priority]) => (
                    <div key={`${platform}-${handle}`} className="contact-priority-item">
                      <div className="contact-info">
                        <div className="integration-icon-small">
                          {React.createElement(getPlatformIcon(platform), { size: 16 })}
                        </div>
                        <div>
                          <div className="contact-handle">{handle}</div>
                          <div className="contact-platform">{platform}</div>
                        </div>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                        <span className={`priority-tier ${priority}`}>{priority}</span>
                        <button className="icon-btn" onClick={() => handleDelete(platform, handle)}>
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>
                  ))
                )
              ) : (
                <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '40px' }}>
                  No manual priorities set yet.
                </p>
              )}
            </div>
          </section>

          <section id="privacy" className="card" style={{ marginTop: '32px' }}>
            <h2>Privacy & Compliance</h2>
            <p className="section-desc">Manage your data preferences and regulatory rights.</p>
            
            <div className="settings-subsection">
              <h3>DPDP Compliance (India)</h3>
              <div className="compliance-options">
                {Object.entries(consentPrefs).map(([purposeId, meta]) => (
                  <div className="compliance-item" key={purposeId}>
                    <div className="compliance-info">
                      <h4>{meta.title || purposeId}</h4>
                      <p>{meta.description}</p>
                    </div>
                    <label className="switch">
                      <input
                        type="checkbox"
                        checked={!!meta.enabled}
                        onChange={(e) => handleConsentChange(purposeId, e.target.checked)}
                        disabled={consentLoadingPurpose === purposeId || (meta.required_for_service && meta.enabled)}
                      />
                      <span className={`slider round ${consentLoadingPurpose === purposeId ? 'opacity-50' : ''}`}></span>
                    </label>
                    {consentLoadingPurpose === purposeId && <Loader2 size={16} className="spin ml-2" style={{ marginLeft: '8px', color: 'var(--primary-blue)' }} />}
                  </div>
                ))}
                {consentStatus && (
                  <span className={`status-msg ${consentStatus.includes('failed') ? 'error' : 'success'}`} style={{ fontSize: '0.85rem' }}>
                    {consentStatus}
                  </span>
                )}

                <div className="compliance-item">
                  <div className="compliance-info">
                    <h4>Right to Nominate</h4>
                    <p>Nominate an individual to exercise your rights in case of death or incapacity.</p>
                  </div>
                  <button className="btn btn-secondary btn-sm" onClick={() => setShowNominateModal(true)}>
                    Set Nominee
                  </button>
                </div>

                <div className="compliance-item grievance">
                  <div className="compliance-info">
                    <h4>Grievance Redressal</h4>
                    <p>Contact our Data Protection Officer for any privacy concerns.</p>
                    <div className="dpo-details">
                      <strong>DPO:</strong> Privacy Team<br />
                      <strong>Email:</strong> dpo@clutsch.com<br />
                      <strong>Response Time:</strong> Within 7 days
                    </div>
                  </div>
                  <button className="btn btn-secondary btn-sm" onClick={() => setShowGrievanceModal(true)}>
                    Log Grievance
                  </button>
                </div>
              </div>
            </div>

            <div className="settings-subsection" style={{ marginTop: '24px' }}>
              <h3>Data Management</h3>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <button className="btn btn-secondary" onClick={handleExport}>
                  <Mail size={18} />
                  <span>Export My Data</span>
                </button>
                {exportStatus && <span className="status-msg success">{exportStatus}</span>}
              </div>
            </div>
          </section>

          <section id="danger-zone" className="card" style={{ marginTop: '32px', borderColor: '#fee2e2' }}>
            <h2 style={{ color: '#ef4444' }}>Danger Zone</h2>
            <p className="section-desc">Once you delete your account, there is no going back. Please be certain.</p>
            <button 
              className="btn btn-secondary" 
              style={{ color: '#ef4444', borderColor: '#fecaca' }}
              onClick={handleDeleteAccount}
            >
              <Trash2 size={18} />
              <span>Delete Account</span>
            </button>
          </section>
        </main>
      </div>

      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal-card" onClick={e => e.stopPropagation()} style={{ maxWidth: '400px' }}>
            <div className="modal-header">
              <h2>Add Contact Priority</h2>
              <button className="close-btn" onClick={() => setShowAddModal(false)}><X size={24} /></button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>Platform</label>
                <select 
                  style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid var(--glass-border)' }}
                  value={newContact.platform}
                  onChange={e => setNewContact({...newContact, platform: e.target.value})}
                >
                  <option value="gmail">Gmail</option>
                  <option value="slack">Slack</option>
                  <option value="outlook">Outlook</option>
                  <option value="jira">Jira</option>
                </select>
              </div>
              <div className="form-group">
                <label>Contact Handle (Email or ID)</label>
                <input 
                  type="text" 
                  placeholder="e.g. boss@company.com" 
                  value={newContact.handle}
                  onChange={e => setNewContact({...newContact, handle: e.target.value})}
                />
              </div>
              <div className="form-group">
                <label>Priority Level</label>
                <select 
                  style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid var(--glass-border)' }}
                  value={newContact.priority}
                  onChange={e => setNewContact({...newContact, priority: e.target.value})}
                >
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowAddModal(false)}>Cancel</button>
              <button className="btn btn-primary" onClick={handleAdd} disabled={!newContact.handle}>Save Priority</button>
            </div>
          </div>
        </div>
      )}

      {showNominateModal && (
        <div className="modal-overlay" onClick={() => setShowNominateModal(false)}>
          <div className="modal-card" onClick={e => e.stopPropagation()} style={{ maxWidth: '450px' }}>
            <div className="modal-header">
              <h2>Register Nominee (DPDP Act)</h2>
              <button className="close-btn" onClick={() => setShowNominateModal(false)}><X size={24} /></button>
            </div>
            <div className="modal-body">
              <p className="modal-intro">India's DPDP Act grants you the right to nominate an individual to exercise your data rights in the event of death or incapacity.</p>
              <div className="form-group">
                <label>Full Name</label>
                <input 
                  type="text" 
                  value={nominee.name}
                  onChange={e => setNominee({...nominee, name: e.target.value})}
                  placeholder="Full name of nominee"
                />
              </div>
              <div className="form-group">
                <label>Email Address</label>
                <input 
                  type="email" 
                  value={nominee.email}
                  onChange={e => setNominee({...nominee, email: e.target.value})}
                  placeholder="nominee@example.com"
                />
              </div>
              <div className="form-group">
                <label>Relationship</label>
                <input 
                  type="text" 
                  value={nominee.relationship}
                  onChange={e => setNominee({...nominee, relationship: e.target.value})}
                  placeholder="e.g. Legal Heir, Spouse, Parent"
                />
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowNominateModal(false)}>Cancel</button>
              <button className="btn btn-primary" onClick={handleNominate} disabled={!nominee.name || !nominee.email}>Register Nominee</button>
            </div>
          </div>
        </div>
      )}

      {showGrievanceModal && (
        <div className="modal-overlay" onClick={() => setShowGrievanceModal(false)}>
          <div className="modal-card" onClick={e => e.stopPropagation()} style={{ maxWidth: '500px' }}>
            <div className="modal-header">
              <h2>Lodge Privacy Grievance</h2>
              <button className="close-btn" onClick={() => setShowGrievanceModal(false)}><X size={24} /></button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label>Subject</label>
                <select 
                  style={{ width: '100%', padding: '10px', borderRadius: '8px', border: '1px solid var(--glass-border)' }}
                  value={grievance.subject}
                  onChange={e => setGrievance({...grievance, subject: e.target.value})}
                >
                  <option value="Data Access">Data Access Request</option>
                  <option value="Correction">Data Correction</option>
                  <option value="Erasure">Right to be Forgotten (Erasure)</option>
                  <option value="Withdrawal">Withdrawal of Consent</option>
                  <option value="Security">Security Concern</option>
                  <option value="Other">Other Privacy Issue</option>
                </select>
              </div>
              <div className="form-group">
                <label>Description of Concern</label>
                <textarea 
                  rows="4"
                  style={{ width: '100%', padding: '12px', borderRadius: '8px', border: '1px solid var(--glass-border)', resize: 'vertical' }}
                  value={grievance.description}
                  onChange={e => setGrievance({...grievance, description: e.target.value})}
                  placeholder="Please provide details about your concern..."
                ></textarea>
              </div>
              <p className="modal-note">Our Data Protection Officer will review your grievance and respond within 7 days.</p>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowGrievanceModal(false)}>Cancel</button>
              <button className="btn btn-primary" onClick={handleGrievance} disabled={!grievance.description}>Submit Grievance</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Settings;
