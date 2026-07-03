import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Joyride } from 'react-joyride';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import DelegationModal from '../components/DelegationModal';
import { 
  MessageSquare, 
  Mail, 
  MessageCircle,
  Check,
  Clock,
  ExternalLink,
  Loader2,
  Bug,
  AlertCircle,
  Users,
  LayoutGrid,
  TrendingUp,
  TrendingDown,
  Info,
  Lightbulb,
  Filter,
  Shield,
  UserPlus
} from 'lucide-react';

const getSourceIcon = (source) => {
  if (!source) return MessageSquare;
  switch (source.toLowerCase()) {
    case 'slack': return MessageCircle;
    case 'gmail':
    case 'email':
    case 'outlook': return Mail;
    case 'teams': return Users;
    case 'whatsapp': return MessageCircle;
    case 'jira': return LayoutGrid;
    default: return MessageSquare;
  }
};

const PriorityGauge = ({ score }) => {
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  
  let color = '#10b981'; // Green
  if (score >= 80) color = '#ef4444'; // Red (Urgent)
  else if (score >= 60) color = '#f97316'; // Orange (High)
  else if (score >= 30) color = '#facc15'; // Yellow (Medium)

  return (
    <div className="priority-gauge" role="img" aria-label={`Priority score: ${Math.round(score)} out of 100`}>
      <svg width="100" height="100" aria-hidden="true">
        <circle 
          className="gauge-bg"
          cx="50" cy="50" r={radius} 
          fill="transparent" 
          stroke="#e2e8f0" 
          strokeWidth="8"
        />
        <circle 
          className="gauge-fill"
          cx="50" cy="50" r={radius} 
          fill="transparent" 
          stroke={color} 
          strokeWidth="8"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 50 50)"
        />
        <text x="50" y="55" textAnchor="middle" fontSize="20" fontWeight="bold" fill="var(--text-main)">
          {Math.round(score)}
        </text>
      </svg>
    </div>
  );
};

const ActionableItem = ({ item, isSelected, onSelect }) => {
  const SourceIcon = getSourceIcon(item.source);
  
  const presence = item.presence || [];

  return (
    <div 
      className={`actionable-item card ${isSelected ? 'selected' : ''}`} 
      onClick={() => onSelect(item)}
      role="button"
      tabIndex={0}
      aria-selected={isSelected}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onSelect(item);
        }
      }}
    >
      <div className="item-header">
        <div className="item-source">
          <SourceIcon size={14} />
          <span>{item.source}</span>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {item.delegation && (
            <div className="delegation-badge" title={`Delegated to ${item.delegation.to_username}`}>
              <Users size={12} />
              <span>{item.delegation.to_username?.substring(0, 2).toUpperCase()}</span>
            </div>
          )}
          {item.priorityTier && (
            <span className={`priority-tier ${item.priorityTier}`}>
              {item.priorityTier}
            </span>
          )}
          <div className="item-score-badge">
            {Math.round(item.priorityScore)}
          </div>
        </div>
      </div>
      <div className="item-body">
        <h4 className="item-title">{item.text}</h4>
        <p className="item-snippet">{item.ai_summary || item.text.substring(0, 60) + '...'}</p>
        
        {presence.length > 0 && (
          <div className="presence-indicators">
            {presence.slice(0, 3).map(p => (
              <div key={p.user_id} className="presence-avatar active" title={`${p.username} is ${p.action}`}>
                {p.username?.substring(0, 2).toUpperCase()}
              </div>
            ))}
            {presence.length > 3 && <span className="presence-more">+{presence.length - 3}</span>}
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginLeft: '8px', alignSelf: 'center' }}>
              Team active
            </span>
          </div>
        )}
      </div>
    </div>
  );
};

const FocusPanel = ({ item, onArchive, onSnooze, onOpen, onDelegate, presence = [] }) => {
  if (!item) {
    return (
      <div className="focus-panel card empty">
        <Info size={48} />
        <h3>No Item Selected</h3>
        <p>Select an item from the list to view details and take action.</p>
      </div>
    );
  }

  return (
    <div className="focus-panel card">
      <div className="focus-header">
        <div className="focus-title-area">
          <div className="focus-source">
            {React.createElement(getSourceIcon(item.source), { size: 16 })}
            <span>{item.source}</span>
            {item.priorityTier && (
              <span className={`priority-tier ${item.priorityTier}`} style={{ marginLeft: '8px' }}>
                {item.priorityTier}
              </span>
            )}
            {item.delegation && (
              <span className="delegated-tag" style={{ marginLeft: '8px' }}>
                Delegated to {item.delegation.to_username}
              </span>
            )}
          </div>
          <h2>{item.text}</h2>
          {item.action_suggested && (
            <div className="action-suggested-badge">
              <Lightbulb size={14} />
              <span>Suggested: {item.action_suggested}</span>
            </div>
          )}
        </div>
        <PriorityGauge score={item.priorityScore} />
      </div>

      {presence.length > 0 && (
        <div className="focus-presence">
          <div className="presence-list">
            {presence.map(p => (
              <div key={p.user_id} className="presence-item">
                <span className={`presence-dot ${p.action}`}></span>
                <span><strong>{p.username}</strong> is {p.action}...</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="focus-actions">
        <button className="focus-action-btn primary" onClick={() => onArchive(item.id)}>
          <Check size={20} />
          <span>Mark Done</span>
        </button>
        <button className="focus-action-btn" onClick={onDelegate}>
          <UserPlus size={20} />
          <span>Delegate</span>
        </button>
        <div className="snooze-group">
          <button className="focus-action-btn" onClick={() => onSnooze(item.id, 60)}>
            <Clock size={20} />
            <span>Snooze</span>
          </button>
          <div className="snooze-options">
            <button onClick={() => onSnooze(item.id, 60)}>1h</button>
            <button onClick={() => onSnooze(item.id, 240)}>4h</button>
            <button onClick={() => onSnooze(item.id, 1440)}>24h</button>
          </div>
        </div>
        {item.source_url && (
          <button className="focus-action-btn" onClick={() => onOpen(item.source_url)}>
            <ExternalLink size={20} />
            <span>Open Original</span>
          </button>
        )}
      </div>

      <div className="focus-section">
        <h3>AI Reasoning</h3>
        <div className="reasoning-card">
          <p>{item.explanation || item.ai_summary || "No specific reasoning provided."}</p>
          <div className="signals">
            <div className="signal-item">
              <TrendingUp size={16} color="#ef4444" />
              <span>Urgency: {Math.round((item.urgency || 0) * 100)}%</span>
            </div>
            <div className="signal-item">
              <TrendingUp size={16} color="#3b82f6" />
              <span>Importance: {Math.round((item.importance || 0) * 100)}%</span>
            </div>
          </div>
        </div>
      </div>

      {item.metadata && (
        <div className="focus-section">
          <h3>Metadata</h3>
          <div className="metadata-grid">
            {Object.entries(item.metadata).map(([key, value]) => (
              typeof value !== 'object' && value !== null && (
                <div key={key} className="meta-item">
                  <span className="meta-label">{key.replace(/_/g, ' ')}:</span>
                  <span className="meta-value">{String(value)}</span>
                </div>
              )
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const Dashboard = () => {
  const [searchParams] = useSearchParams();
  const [runTour, setRunTour] = useState(false);
  const [items, setItems] = useState([]);
  const [selectedItem, setSelectedItem] = useState(null);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState(null);
  const [selectedTier, setSelectedTier] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState('personal'); // 'personal' or 'team'
  const [isDelegationModalOpen, setIsDelegationModalOpen] = useState(false);
  const [itemPresence, setItemPresence] = useState([]);

  const tourSteps = [
    {
      target: '.priority-gauge',
      content: 'This is your Priority Score. Our AI calculates this from 0 to 100 based on urgency and importance.',
      placement: 'left',
    },
    {
      target: '.reasoning-card',
      content: 'Understand the "Why". We show you exactly which signals triggered this priority.',
      placement: 'top',
    },
    {
      target: '.focus-actions',
      content: 'Quickly Mark Done, Delegate, or Snooze items to keep your flow moving.',
      placement: 'bottom',
    },
    {
      target: '.actionable-items-list',
      content: 'Your unified feed. All your connected channels ranked by what needs your attention now.',
      placement: 'right',
    }
  ];

  useEffect(() => {
    if (searchParams.get('tour') === 'true') {
      setRunTour(true);
    }
  }, [searchParams]);

  const tiers = ['all', 'urgent', 'high', 'medium', 'low'];

  const filteredItems = items.filter(item => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      item.text?.toLowerCase().includes(query) ||
      item.source?.toLowerCase().includes(query) ||
      item.ai_summary?.toLowerCase().includes(query) ||
      item.explanation?.toLowerCase().includes(query)
    );
  });

  const fetchItems = useCallback(async () => {
    try {
      let url = '/priorities/feed';
      if (viewMode === 'team') {
        url = '/team/feed';
      } else if (selectedTier !== 'all') {
        url = `/priorities/feed?tier=${selectedTier}`;
      }
      
      const data = await api.get(url);
      setItems(data);
    } catch (err) {
      console.error("Failed to fetch items:", err);
    } finally {
      setLoading(false);
    }
  }, [selectedTier, viewMode]);

  useEffect(() => {
    setLoading(true);
    fetchItems();
  }, [selectedTier, viewMode, fetchItems]);

  useEffect(() => {
    const interval = setInterval(fetchItems, 30000);
    return () => clearInterval(interval);
  }, [fetchItems]);

  // Presence polling for selected item
  useEffect(() => {
    if (!selectedItem) {
      setItemPresence([]);
      return;
    }

    const fetchPresence = async () => {
      try {
        const data = await api.get(`/team/items/${selectedItem.id}/presence`);
        setItemPresence(data);
      } catch (err) {
        console.error("Presence fetch failed:", err);
      }
    };

    fetchPresence();
    const interval = setInterval(fetchPresence, 5000);
    
    // Update our own presence
    api.post(`/team/items/${selectedItem.id}/presence`, { action: 'viewing' }).catch(() => {});

    return () => clearInterval(interval);
  }, [selectedItem]);

  useEffect(() => {
    if (filteredItems.length > 0 && (!selectedItem || !filteredItems.find(i => i.id === selectedItem.id))) {
      setSelectedItem(filteredItems[0]);
    } else if (filteredItems.length === 0) {
      setSelectedItem(null);
    }
  }, [filteredItems, selectedItem]);

  const handleArchive = async (id) => {
    try {
      await api.post(`/items/${id}/archive`);
      setItems(prev => prev.filter(i => i.id !== id));
      showToast("Item archived");
    } catch (err) {
      console.error("Archive failed:", err);
    }
  };

  const handleSnooze = async (id, duration = 60) => {
    try {
      await api.post(`/items/${id}/snooze`, { hours: duration / 60 });
      setItems(prev => prev.filter(i => i.id !== id));
      showToast(`Snoozed for ${duration}m`);
    } catch (err) {
      console.error("Snooze failed:", err);
    }
  };

  const handleDelegate = (itemId, member, note) => {
    setItems(prev => prev.filter(i => i.id !== itemId));
    showToast(`Delegated to ${member.name || member.username}`);
  };

  const handleOpen = (url) => {
    window.open(url, '_blank');
  };

  const showToast = (message) => {
    setToast(message);
    setTimeout(() => setToast(null), 3000);
  };

  return (
    <div className="dashboard-3column">
      <Joyride 
        steps={tourSteps} 
        run={runTour} 
        continuous 
        showSkipButton 
        showProgress 
        styles={{
          options: {
            primaryColor: '#3b82f6',
            backgroundColor: '#1e293b',
            textColor: '#f8fafc',
            arrowColor: '#1e293b',
          }
        }}
      />
      <section className="actionable-items-list">
        <div className="section-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <h2>Priority Feed</h2>
            {loading && <Loader2 className="spin" size={18} />}
          </div>
          <span className="item-count">{filteredItems.length} items</span>
        </div>

        <div className="feed-controls" style={{ padding: '0 16px 16px' }}>
          <div className="view-toggle glass">
            <button 
              className={`toggle-btn ${viewMode === 'personal' ? 'active' : ''}`}
              onClick={() => setViewMode('personal')}
            >
              Personal
            </button>
            <button 
              className={`toggle-btn ${viewMode === 'team' ? 'active' : ''}`}
              onClick={() => setViewMode('team')}
            >
              Team Feed
            </button>
          </div>

          <div className="search-bar" style={{ marginBottom: '12px' }}>
            <input 
              type="text" 
              placeholder="Search items..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ width: '100%', padding: '8px 12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}
            />
          </div>
          <div className="feed-filters">
            {tiers.map(tier => (
              <button 
                key={tier}
                className={`tier-chip ${selectedTier === tier ? 'active' : ''} ${tier}`}
                onClick={() => setSelectedTier(tier)}
              >
                {tier}
              </button>
            ))}
          </div>
        </div>

        <div className="items-scroll">
          {filteredItems.map(item => (
            <ActionableItem 
              key={item.id} 
              item={item} 
              isSelected={selectedItem?.id === item.id}
              onSelect={setSelectedItem}
            />
          ))}
          {!loading && filteredItems.length === 0 && (
            <div className="empty-msg" style={{ textAlign: 'center', padding: '40px 20px' }}>
              <Check size={48} style={{ color: 'var(--success-green)', marginBottom: '16px' }} />
              <p>
                {searchQuery 
                  ? `No results for "${searchQuery}"`
                  : viewMode === 'team' 
                    ? "No high-priority team items at the moment."
                    : `All clear in the ${selectedTier} tier!`
                }
              </p>
            </div>
          )}
        </div>
      </section>

      <section className="focus-panel-container">
        <FocusPanel 
          item={selectedItem} 
          onArchive={handleArchive}
          onSnooze={handleSnooze}
          onOpen={handleOpen}
          onDelegate={() => setIsDelegationModalOpen(true)}
          presence={itemPresence}
        />
      </section>

      <DelegationModal 
        isOpen={isDelegationModalOpen}
        onClose={() => setIsDelegationModalOpen(false)}
        item={selectedItem}
        onDelegate={handleDelegate}
      />

      {toast && (
        <div className="toast-container">
          <div className="toast">{toast}</div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
