import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Joyride } from 'react-joyride';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import DelegationModal from '../components/DelegationModal';
import useWebSocket from '../utils/useWebSocket';
import { showToast, registerToastHandler, ToastContainer } from '../utils/toast';
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
  UserPlus,
  X
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
        <text x="50" y="55" textAnchor="middle" fontSize="20" fontWeight="bold" fill="var(--text-primary)">
          {Math.round(score)}
        </text>
      </svg>
    </div>
  );
};

const ActionableItem = ({ item, isSelected, onSelect, onToggleSelect, showCheckbox }) => {
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
      {showCheckbox && (
        <div className="item-checkbox" onClick={(e) => { e.stopPropagation(); onToggleSelect(item); }}>
          <input 
            type="checkbox" 
            checked={isSelected} 
            onChange={() => onToggleSelect(item)}
            aria-label={`Select item: ${item.text}`}
          />
        </div>
      )}
      <div className="item-header">
        <div className="item-source">
          {React.createElement(getSourceIcon(item.source), { size: 14 })}
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
  const { user } = useAuth();
  const [runTour, setRunTour] = useState(false);
  const [items, setItems] = useState([]);
  const [selectedItem, setSelectedItem] = useState(null);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState(null);
  const [selectedTier, setSelectedTier] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [sourceFilter, setSourceFilter] = useState('all');
  const [dateFilter, setDateFilter] = useState('all');
  const [scoreThreshold, setScoreThreshold] = useState(0);
  const [viewMode, setViewMode] = useState('personal');
  const [isDelegationModalOpen, setIsDelegationModalOpen] = useState(false);
  const [itemPresence, setItemPresence] = useState([]);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [bulkActionLoading, setBulkActionLoading] = useState(false);
  const [initialLoad, setInitialLoad] = useState(true);

  // Register toast handler
  useEffect(() => {
    registerToastHandler((msg, type) => {
      setToast({ message: msg, type: type || 'success' });
      setTimeout(() => setToast(null), 3000);
    });
  }, []);

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
      setInitialLoad(false);
    } catch {
      // Silently fail — polling will retry
    } finally {
      setLoading(false);
    }
  }, [selectedTier, viewMode]);

  // WebSocket for real-time updates. Wrapped in useCallback so useWebSocket
  // gets a stable onMessage across renders instead of a fresh inline
  // function every time — an unstable callback here would make
  // useWebSocket's internal `connect` (which depends on onMessage) change
  // identity every render, tearing down and re-establishing the socket
  // far more often than intended.
  const handleWsMessage = useCallback((data) => {
    if (data.type === 'feed_update') {
      fetchItems();
    }
  }, [fetchItems]);

  useWebSocket('t-acme', user?.id || 'anonymous', handleWsMessage);

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
  const dateRanges = [
    { value: 'all', label: 'All time' },
    { value: '24h', label: 'Past 24h' },
    { value: '7d', label: 'Past 7 days' },
    { value: '30d', label: 'Past 30 days' }
  ];

  const getDateCutoff = (range, now) => {
    switch (range) {
      case '24h': return now - 24 * 60 * 60 * 1000;
      case '7d': return now - 7 * 24 * 60 * 60 * 1000;
      case '30d': return now - 30 * 24 * 60 * 60 * 1000;
      default: return 0;
    }
  };

  // Computed once per render rather than inside getDateCutoff/the filter
  // callback below — calling Date.now() from deep inside a render-time
  // computation is what the linter flags as impure.
  const nowMs = Date.now();

  const filteredItems = items.filter(item => {
    // Keyword search
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      if (!(item.text?.toLowerCase().includes(query) ||
            item.source?.toLowerCase().includes(query) ||
            item.ai_summary?.toLowerCase().includes(query) ||
            item.explanation?.toLowerCase().includes(query))) {
        return false;
      }
    }
    // Source filter
    if (sourceFilter !== 'all' && item.source?.toLowerCase() !== sourceFilter) {
      return false;
    }
    // Date range filter
    if (dateFilter !== 'all') {
      const cutoff = getDateCutoff(dateFilter, nowMs);
      const itemTime = (item.timestamp || 0) * 1000;
      if (itemTime < cutoff) return false;
    }
    // Score threshold
    if ((item.priorityScore || 0) < scoreThreshold) {
      return false;
    }
    return true;
  });

  const availableSources = ['all', ...new Set(items.map(i => i.source?.toLowerCase()).filter(Boolean))];

  // Bulk actions
  const toggleSelectItem = (item) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(item.id)) {
        next.delete(item.id);
      } else {
        next.add(item.id);
      }
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selectedIds.size === filteredItems.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(filteredItems.map(i => i.id)));
    }
  };

  const handleBulkArchive = async () => {
    if (selectedIds.size === 0) return;
    setBulkActionLoading(true);
    try {
      await api.post('/items/bulk/archive', { item_ids: Array.from(selectedIds) });
      setItems(prev => prev.filter(i => !selectedIds.has(i.id)));
      showToast(`Archived ${selectedIds.size} items`, 'success');
      setSelectedIds(new Set());
    } catch {
      // Fallback: archive one by one
      let successCount = 0;
      for (const id of selectedIds) {
        try {
          await api.post(`/items/${id}/archive`);
          successCount++;
        } catch { /* skip */ }
      }
      setItems(prev => prev.filter(i => !selectedIds.has(i.id)));
      showToast(`Archived ${successCount} items`, 'success');
      setSelectedIds(new Set());
    } finally {
      setBulkActionLoading(false);
    }
  };

  const handleBulkSnooze = async (duration = 60) => {
    if (selectedIds.size === 0) return;
    setBulkActionLoading(true);
    try {
      await api.post('/items/bulk/snooze', { item_ids: Array.from(selectedIds), hours: duration / 60 });
      setItems(prev => prev.filter(i => !selectedIds.has(i.id)));
      showToast(`Snoozed ${selectedIds.size} items for ${duration}m`, 'success');
      setSelectedIds(new Set());
    } catch {
      // Fallback: snooze one by one
      let successCount = 0;
      for (const id of selectedIds) {
        try {
          await api.post(`/items/${id}/snooze`, { hours: duration / 60 });
          successCount++;
        } catch { /* skip */ }
      }
      setItems(prev => prev.filter(i => !selectedIds.has(i.id)));
      showToast(`Snoozed ${successCount} items`, 'success');
      setSelectedIds(new Set());
    } finally {
      setBulkActionLoading(false);
    }
  };

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
      } catch {
        // Silently fail
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
    } catch {
      showToast("Failed to archive item", "error");
    }
  };

  const handleSnooze = async (id, duration = 60) => {
    try {
      await api.post(`/items/${id}/snooze`, { hours: duration / 60 });
      setItems(prev => prev.filter(i => i.id !== id));
      showToast(`Snoozed for ${duration}m`);
    } catch {
      showToast("Failed to snooze item", "error");
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
        <div className="section-header" style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h2 style={{ margin: 0, fontSize: '1.1rem' }}>Priority Feed</h2>
            {loading && <Loader2 className="spin" size={16} />}
          </div>
          <input 
            type="text" 
            placeholder="Search..." 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ flex: 1, minWidth: '140px', maxWidth: '260px', padding: '6px 12px', borderRadius: '9999px', border: '1px solid var(--glass-border)', background: 'var(--glass-fill)', backdropFilter: 'blur(12px)', fontSize: '0.8rem', fontFamily: 'var(--font-family)', color: 'var(--text-primary)', outline: 'none' }}
            aria-label="Search items"
          />
          <span className="item-count">{filteredItems.length} items</span>
        </div>

        {/* Compact filter bar */}
        <div className="feed-controls" style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', alignItems: 'center', padding: '0 0 8px 0' }}>
          <div className="view-toggle" style={{ display: 'flex', borderRadius: '9999px', background: 'var(--glass-fill)', backdropFilter: 'blur(12px)', border: '1px solid var(--glass-border)', overflow: 'hidden', flexShrink: 0 }}>
            <button 
              className={`toggle-btn ${viewMode === 'personal' ? 'active' : ''}`}
              onClick={() => setViewMode('personal')}
              style={{ padding: '4px 12px', fontSize: '0.75rem', border: 'none', background: viewMode === 'personal' ? 'var(--accent)' : 'transparent', color: viewMode === 'personal' ? '#fff' : 'var(--text-secondary)', cursor: 'pointer', fontFamily: 'var(--font-family)', fontWeight: 500, transition: 'all 0.2s' }}
            >
              Personal
            </button>
            <button 
              className={`toggle-btn ${viewMode === 'team' ? 'active' : ''}`}
              onClick={() => setViewMode('team')}
              style={{ padding: '4px 12px', fontSize: '0.75rem', border: 'none', background: viewMode === 'team' ? 'var(--accent)' : 'transparent', color: viewMode === 'team' ? '#fff' : 'var(--text-secondary)', cursor: 'pointer', fontFamily: 'var(--font-family)', fontWeight: 500, transition: 'all 0.2s' }}
            >
              Team
            </button>
          </div>

          {/* Source filter */}
          <div className="filter-row" style={{ display: 'flex', gap: '3px', flexWrap: 'wrap', alignItems: 'center' }}>
            {availableSources.map(src => (
              <button 
                key={src}
                className={`tier-chip ${sourceFilter === src ? 'active' : ''}`}
                onClick={() => setSourceFilter(src)}
                style={{ fontSize: '0.7rem', padding: '2px 8px', borderRadius: '9999px', border: '1px solid var(--glass-border)', background: sourceFilter === src ? 'var(--accent)' : 'var(--glass-fill)', color: sourceFilter === src ? '#fff' : 'var(--text-secondary)', cursor: 'pointer', fontFamily: 'var(--font-family)', transition: 'all 0.2s', backdropFilter: 'blur(8px)' }}
              >
                {src === 'all' ? 'All' : src.charAt(0).toUpperCase() + src.slice(1)}
              </button>
            ))}
          </div>

          {/* Date range filter */}
          <div className="filter-row" style={{ display: 'flex', gap: '3px', flexWrap: 'wrap', alignItems: 'center' }}>
            {dateRanges.map(dr => (
              <button 
                key={dr.value}
                className={`tier-chip ${dateFilter === dr.value ? 'active' : ''}`}
                onClick={() => setDateFilter(dr.value)}
                style={{ fontSize: '0.7rem', padding: '2px 8px', borderRadius: '9999px', border: '1px solid var(--glass-border)', background: dateFilter === dr.value ? 'var(--accent)' : 'var(--glass-fill)', color: dateFilter === dr.value ? '#fff' : 'var(--text-secondary)', cursor: 'pointer', fontFamily: 'var(--font-family)', transition: 'all 0.2s', backdropFilter: 'blur(8px)' }}
              >
                {dr.label}
              </button>
            ))}
          </div>

          {/* Score threshold */}
          <div className="filter-row" style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{scoreThreshold}+</span>
            <input 
              type="range" 
              min="0" max="100" step="5"
              value={scoreThreshold}
              onChange={(e) => setScoreThreshold(Number(e.target.value))}
              style={{ width: '60px', height: '4px', accentColor: 'var(--accent)' }}
              aria-label={`Minimum priority score: ${scoreThreshold}`}
            />
          </div>

          {/* Tier filter */}
          <div className="feed-filters" style={{ display: 'flex', gap: '3px' }}>
            {tiers.map(tier => (
              <button 
                key={tier}
                className={`tier-chip ${selectedTier === tier ? 'active' : ''} ${tier}`}
                onClick={() => setSelectedTier(tier)}
                style={{ fontSize: '0.7rem', padding: '2px 8px', borderRadius: '9999px', border: '1px solid var(--glass-border)', background: selectedTier === tier ? 'var(--accent)' : 'var(--glass-fill)', color: selectedTier === tier ? '#fff' : 'var(--text-secondary)', cursor: 'pointer', fontFamily: 'var(--font-family)', transition: 'all 0.2s', backdropFilter: 'blur(8px)', textTransform: 'capitalize' }}
              >
                {tier}
              </button>
            ))}
          </div>

          {/* Select All */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginLeft: 'auto' }}>
            <input 
              type="checkbox" 
              checked={selectedIds.size > 0 && selectedIds.size === filteredItems.length}
              onChange={toggleSelectAll}
              style={{ accentColor: 'var(--accent)', width: '14px', height: '14px', cursor: 'pointer' }}
              aria-label="Select all items"
            />
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              {selectedIds.size > 0 ? `${selectedIds.size}` : ''}
            </span>
          </div>
        </div>

        {/* Bulk action toolbar */}
        {selectedIds.size > 0 && (
          <div className="bulk-action-bar" style={{
            position: 'sticky', bottom: 0, left: 0, right: 0,
            background: 'rgba(30, 41, 59, 0.95)', backdropFilter: 'blur(12px)',
            padding: '12px 16px', display: 'flex', gap: '8px', alignItems: 'center',
            borderTop: '1px solid var(--glass-border)', zIndex: 10
          }}>
            <span style={{ color: 'var(--text-primary)', fontSize: '0.85rem', marginRight: 'auto' }}>
              {selectedIds.size} selected
            </span>
            <button className="btn btn-primary btn-sm" onClick={handleBulkArchive} disabled={bulkActionLoading}>
              {bulkActionLoading ? <Loader2 className="spin" size={16} /> : <Check size={16} />}
              <span>Archive</span>
            </button>
            <button className="btn btn-secondary btn-sm" onClick={() => handleBulkSnooze(60)} disabled={bulkActionLoading}>
              <Clock size={16} />
              <span>Snooze 1h</span>
            </button>
            <button className="btn btn-secondary btn-sm" onClick={() => handleBulkSnooze(240)} disabled={bulkActionLoading}>
              <Clock size={16} />
              <span>Snooze 4h</span>
            </button>
            <button className="btn btn-secondary btn-sm" onClick={() => setSelectedIds(new Set())}>
              <X size={16} />
              <span>Cancel</span>
            </button>
          </div>
        )}

        <div className="items-scroll">
          {filteredItems.map(item => (
            <ActionableItem 
              key={item.id} 
              item={item} 
              isSelected={selectedIds.has(item.id) || selectedItem?.id === item.id}
              onSelect={setSelectedItem}
              onToggleSelect={toggleSelectItem}
              showCheckbox={true}
            />
          ))}
          {loading && initialLoad && (
            <div className="loading-state" style={{ textAlign: 'center', padding: '60px 20px' }} role="status">
              <Loader2 size={48} className="spin" style={{ color: 'var(--primary-blue)', marginBottom: '16px' }} />
              <p style={{ color: 'var(--text-muted)' }}>Loading your priority feed...</p>
            </div>
          )}
          {!loading && !initialLoad && filteredItems.length === 0 && (
            <div className="empty-msg" style={{ textAlign: 'center', padding: '60px 20px' }} role="status">
              <Check size={48} style={{ color: 'var(--success-green)', marginBottom: '16px' }} />
              <p>
                {searchQuery || sourceFilter !== 'all' || dateFilter !== 'all' || scoreThreshold > 0
                  ? `No items match your filters. Try adjusting your search criteria.`
                  : viewMode === 'team' 
                    ? "No high-priority team items at the moment."
                    : `All clear in the ${selectedTier} tier!`
                }
              </p>
              {(searchQuery || sourceFilter !== 'all' || dateFilter !== 'all' || scoreThreshold > 0) && (
                <button 
                  className="btn btn-secondary btn-sm" 
                  style={{ marginTop: '12px' }}
                  onClick={() => { setSearchQuery(''); setSourceFilter('all'); setDateFilter('all'); setScoreThreshold(0); }}
                >
                  Clear Filters
                </button>
              )}
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

      <ToastContainer toast={toast} onClear={() => setToast(null)} />
    </div>
  );
};

export default Dashboard;
