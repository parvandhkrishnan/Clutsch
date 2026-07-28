import { useState, useEffect } from 'react';
import api from '../utils/api';
import IntegrationModal from '../components/IntegrationModal';
import IntegrationSettingsModal from '../components/IntegrationSettingsModal';
import {
  Mail,
  MessageCircle,
  CheckCircle2,
  Users,
  LayoutGrid,
  List,
  Settings,
  RefreshCw,
  Loader2
} from 'lucide-react';

const IntegrationCard = ({ id, name, icon: Icon, description, connected, isConnecting, isSyncing, onConnect, onSync, onManage }) => (
  <div className={`integration-card card ${connected ? 'connected' : ''}`}>
    <div className="integration-header">
      <div className="integration-icon-bg">
        <Icon size={24} />
      </div>
      {connected && (
        <div className="connected-badge">
          <CheckCircle2 size={16} />
          <span>Connected</span>
        </div>
      )}
    </div>
    <div className="integration-body">
      <h3>{name}</h3>
      <p>{description}</p>
    </div>
    <div className="integration-actions">
      {connected ? (
        <>
          <button 
            className="sync-btn"
            onClick={() => onSync(id)}
            disabled={isSyncing}
          >
            {isSyncing ? <RefreshCw size={16} className="spin" /> : <RefreshCw size={16} />}
            <span>Sync</span>
          </button>
          <button 
            className="connect-btn secondary"
            onClick={() => onManage(id)}
          >
            Manage
          </button>
        </>
      ) : (
        <button 
          className="connect-btn"
          onClick={() => onConnect(id)}
          disabled={isConnecting}
        >
          {isConnecting ? <Loader2 size={16} className="spin" /> : 'Connect'}
        </button>
      )}
    </div>
  </div>
);

const IntegrationRow = ({ id, name, icon: Icon, account, connected, lastSync, isSyncing, onSync, onManage }) => (
  <div className="integration-row">
    <div className="integration-row-cell service">
      <div className="integration-icon-small">
        <Icon size={20} />
      </div>
      <span>{name}</span>
    </div>
    <div className="integration-row-cell account">
      {connected ? account : '-'}
    </div>
    <div className="integration-row-cell status">
      {connected ? (
        <div className="status-indicator active">
          <div className="status-dot"></div>
          <span>Active</span>
        </div>
      ) : (
        <div className="status-indicator inactive">
          <div className="status-dot"></div>
          <span>Inactive</span>
        </div>
      )}
    </div>
    <div className="integration-row-cell sync">
      {connected ? lastSync : '-'}
    </div>
    <div className="integration-row-cell actions">
      {connected && (
        <button 
          className="icon-btn" 
          onClick={() => onSync(id)}
          disabled={isSyncing}
          title="Sync Now"
        >
          <RefreshCw size={18} className={isSyncing ? 'spin' : ''} />
        </button>
      )}
      <button className="icon-btn" title="Settings" onClick={() => onManage(id)}><Settings size={18} /></button>
    </div>
  </div>
);

const Integrations = () => {
  const [viewMode, setViewMode] = useState('gallery');
  const [loading, setLoading] = useState(true);
  const [integrations, setIntegrations] = useState([]);
  const [actionStates, setActionStates] = useState({}); // { id: { isConnecting: bool, isSyncing: bool } }
  
  // Modal states
  const [isConnectModalOpen, setIsConnectModalOpen] = useState(false);
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false);
  const [selectedIntegration, setSelectedIntegration] = useState(null);

  const metadata = {
    gmail: { name: 'Gmail', icon: Mail, description: 'Connect your personal or work Gmail account to prioritize emails.', account: 'john.doe@gmail.com' },
    outlook: { name: 'Outlook', icon: Mail, description: 'Sync your Microsoft Outlook inbox for unified communication.', account: 'work@company.com' },
    slack: { name: 'Slack', icon: MessageCircle, description: 'Identify urgent messages and threads across all your Slack channels.', account: 'Team Slack' },
    teams: { name: 'MS Teams', icon: Users, description: 'Collaborate and prioritize messages from Microsoft Teams.', account: 'Work Teams' },
    whatsapp: { name: 'WhatsApp', icon: MessageCircle, description: 'Stay on top of your WhatsApp chats with AI-driven priority.', account: '+123456789' },
    jira: { name: 'Jira', icon: LayoutGrid, description: 'Track project updates and ticket priorities from Jira.', account: 'John Doe' },
  };

  const fetchIntegrations = async () => {
    try {
      const data = await api.get('/integrations');
      
      // Merge backend data with frontend metadata
      const merged = Object.keys(metadata).map(id => ({
        id,
        ...metadata[id],
        connected: data.connected.includes(id),
        available: data.available.includes(id),
        lastSync: data.connected.includes(id) ? 'Just now' : '-', // Mock last sync for now
        settings: {
          enabled: true,
          syncFrequency: 'hourly',
          priorityThreshold: 50,
          notifyUrgent: true,
        }
      }));
      
      setIntegrations(merged);
    } catch (error) {
      console.error('Failed to fetch integrations:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIntegrations();
  }, []);

  const handleOpenConnect = (id) => {
    const integration = integrations.find(i => i.id === id);
    setSelectedIntegration(integration);
    setIsConnectModalOpen(true);
  };

  const handleConnectSuccess = async (id) => {
    try {
      await api.post(`/integrations/${id}/connect`, { token: 'dummy-token' });
      await fetchIntegrations();
    } catch (error) {
      console.error(`Error connecting ${id}:`, error);
    }
  };

  const handleOpenSettings = (id) => {
    const integration = integrations.find(i => i.id === id);
    setSelectedIntegration(integration);
    setIsSettingsModalOpen(true);
  };

  const handleSaveSettings = async (id, settings) => {
    // In a real app: await api.post(`/integrations/${id}/settings`, settings);
    console.log(`Saving settings for ${id}:`, settings);
    setIntegrations(prev => prev.map(item => 
      item.id === id ? { ...item, settings } : item
    ));
    setIsSettingsModalOpen(false);
  };

  const handleSync = async (id) => {
    setActionStates(prev => ({ ...prev, [id]: { ...prev[id], isSyncing: true } }));
    try {
      await api.post(`/integrations/${id}/sync`);
      // Just a mock feedback
      console.log(`Synced ${id}`);
    } catch (error) {
      console.error(`Error syncing ${id}:`, error);
    } finally {
      setTimeout(() => {
        setActionStates(prev => ({ ...prev, [id]: { ...prev[id], isSyncing: false } }));
      }, 1000); // Small delay for visual feedback
    }
  };

  const handleDisconnect = (id) => {
    // Backend doesn't have disconnect yet, so we mock it locally
    setIntegrations(prev => prev.map(item => 
      item.id === id ? { ...item, connected: false } : item
    ));
    setIsSettingsModalOpen(false);
  };

  if (loading) {
    return (
      <div className="loading-container">
        <Loader2 className="spin" size={48} />
        <p>Loading integrations...</p>
      </div>
    );
  }

  return (
    <div className="integrations-page">
      <header className="page-header">
        <div>
          <h1>Integrations Hub</h1>
          <p>Connect and manage your communication channels.</p>
        </div>
        <div className="view-toggle">
          <button 
            className={`toggle-btn ${viewMode === 'gallery' ? 'active' : ''}`}
            onClick={() => setViewMode('gallery')}
            title="Gallery View"
          >
            <LayoutGrid size={20} />
          </button>
          <button 
            className={`toggle-btn ${viewMode === 'list' ? 'active' : ''}`}
            onClick={() => setViewMode('list')}
            title="List View"
          >
            <List size={20} />
          </button>
        </div>
      </header>
      
      {viewMode === 'gallery' ? (
        <div className="integrations-grid">
          {integrations.map(integration => (
            <IntegrationCard 
              key={integration.id}
              {...integration}
              isConnecting={actionStates[integration.id]?.isConnecting}
              isSyncing={actionStates[integration.id]?.isSyncing}
              onConnect={handleOpenConnect}
              onSync={handleSync}
              onManage={handleOpenSettings}
            />
          ))}
        </div>
      ) : (
        <div className="integrations-list-container card">
          <div className="integration-list-header">
            <div className="integration-row-cell service">Service</div>
            <div className="integration-row-cell account">Account</div>
            <div className="integration-row-cell status">Status</div>
            <div className="integration-row-cell sync">Last Sync</div>
            <div className="integration-row-cell actions"></div>
          </div>
          <div className="integration-list-body">
            {integrations.map(integration => (
              <IntegrationRow 
                key={integration.id}
                {...integration}
                isSyncing={actionStates[integration.id]?.isSyncing}
                onSync={handleSync}
                onManage={handleOpenSettings}
              />
            ))}
          </div>
        </div>
      )}

      {selectedIntegration && (
        <>
          <IntegrationModal 
            isOpen={isConnectModalOpen}
            onClose={() => setIsConnectModalOpen(false)}
            integration={selectedIntegration}
            onConnectSuccess={handleConnectSuccess}
          />
          <IntegrationSettingsModal 
            isOpen={isSettingsModalOpen}
            onClose={() => setIsSettingsModalOpen(false)}
            integration={selectedIntegration}
            onSave={handleSaveSettings}
            onDisconnect={handleDisconnect}
          />
        </>
      )}
    </div>
  );
};

export default Integrations;
