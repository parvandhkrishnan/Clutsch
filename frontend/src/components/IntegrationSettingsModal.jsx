import React, { useState, useEffect } from 'react';
import { X, Save, Trash2 } from 'lucide-react';

const IntegrationSettingsModal = ({ isOpen, onClose, integration, onSave, onDisconnect }) => {
  const [settings, setSettings] = useState({
    enabled: true,
    syncFrequency: 'hourly',
    priorityThreshold: 50,
    notifyUrgent: true,
    ...integration.settings
  });

  useEffect(() => {
    const handleEsc = (e) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      window.addEventListener('keydown', handleEsc);
    }
    return () => window.removeEventListener('keydown', handleEsc);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card settings-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: '500px' }}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div className="integration-icon-small" style={{ 
              width: '32px', 
              height: '32px', 
              backgroundColor: '#f1f5f9', 
              borderRadius: '8px', 
              display: 'flex', 
              alignItems: 'center', 
              justifyContent: 'center' 
            }}>
              <integration.icon size={20} color="var(--primary-blue)" />
            </div>
            <h2 style={{ fontSize: '1.25rem' }}>{integration.name} Settings</h2>
          </div>
          <button className="close-btn" onClick={onClose}><X size={24} /></button>
        </div>

        <div className="modal-body" style={{ padding: '24px' }}>
          <div className="settings-section">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
              <div>
                <h4 style={{ margin: '0 0 4px 0' }}>Enable Integration</h4>
                <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                  Allow PriorityFlow to process data from this source.
                </p>
              </div>
              <label className="switch">
                <input 
                  type="checkbox" 
                  checked={settings.enabled} 
                  onChange={(e) => setSettings({...settings, enabled: e.target.checked})}
                />
                <span className="slider round"></span>
              </label>
            </div>

            <div style={{ marginBottom: '24px' }}>
              <h4 style={{ margin: '0 0 8px 0' }}>Priority Threshold: {settings.priorityThreshold}</h4>
              <p style={{ margin: '0 0 16px 0', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                Only show items with a priority score higher than this value.
              </p>
              <input 
                type="range" 
                min="0" 
                max="100" 
                value={settings.priorityThreshold}
                onChange={(e) => setSettings({...settings, priorityThreshold: parseInt(e.target.value)})}
                style={{ width: '100%', cursor: 'pointer' }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '8px' }}>
                <span>Show All</span>
                <span>Only Critical</span>
              </div>
            </div>

            <div style={{ marginBottom: '24px' }}>
              <h4 style={{ margin: '0 0 8px 0' }}>Sync Frequency</h4>
              <select 
                style={{ 
                  width: '100%', 
                  padding: '10px', 
                  borderRadius: '8px', 
                  border: '1px solid var(--border-color)',
                  backgroundColor: 'white'
                }} 
                value={settings.syncFrequency}
                onChange={(e) => setSettings({...settings, syncFrequency: e.target.value})}
              >
                <option value="realtime">Real-time (Push)</option>
                <option value="hourly">Hourly</option>
                <option value="daily">Daily</option>
              </select>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
              <div>
                <h4 style={{ margin: '0 0 4px 0' }}>Urgent Notifications</h4>
                <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                  Notify me immediately for items with priority &gt; 90.
                </p>
              </div>
              <label className="switch">
                <input 
                  type="checkbox" 
                  checked={settings.notifyUrgent}
                  onChange={(e) => setSettings({...settings, notifyUrgent: e.target.checked})}
                />
                <span className="slider round"></span>
              </label>
            </div>
          </div>

          <div className="danger-zone-settings" style={{ borderTop: '1px solid var(--border-color)', paddingTop: '24px', marginTop: '8px' }}>
            <h4 style={{ color: '#ef4444', margin: '0 0 16px 0' }}>Danger Zone</h4>
            <button 
              className="btn btn-secondary" 
              style={{ 
                color: '#ef4444', 
                borderColor: '#fecaca', 
                width: '100%', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center',
                gap: '8px'
              }} 
              onClick={() => onDisconnect(integration.id)}
            >
              <Trash2 size={18} />
              <span>Disconnect Integration</span>
            </button>
          </div>
        </div>

        <div className="modal-footer" style={{ borderTop: '1px solid var(--border-color)', padding: '16px 24px', display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button 
            className="btn btn-primary" 
            style={{ display: 'flex', alignItems: 'center', gap: '8px' }} 
            onClick={() => onSave(integration.id, settings)}
          >
            <Save size={18} />
            <span>Save Settings</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default IntegrationSettingsModal;
