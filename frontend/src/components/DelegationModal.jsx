import { useState, useEffect } from 'react';
import { X, Search, Shield, Clock, Send, Loader2 } from 'lucide-react';
import api from '../utils/api';
import { showToast } from '../utils/toast';
import useFocusTrap from '../utils/useFocusTrap';

const DelegationModal = ({ isOpen, onClose, item, onDelegate }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedMember, setSelectedMember] = useState(null);
  const [delegating, setDelegating] = useState(false);
  const [note, setNote] = useState('');
  const [members, setMembers] = useState([]);
  const [loadingMembers, setLoadingMembers] = useState(false);
  useFocusTrap(isOpen);

  useEffect(() => {
    if (isOpen) {
      const fetchMembers = async () => {
        setLoadingMembers(true);
        try {
          const data = await api.get('/team/members');
          setMembers(data);
        } catch {
          // Silently fail — non-critical
        } finally {
          setLoadingMembers(false);
        }
      };
      fetchMembers();
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const filteredMembers = members.filter(member => 
    (member.name?.toLowerCase().includes(searchQuery.toLowerCase()) || 
     member.username?.toLowerCase().includes(searchQuery.toLowerCase())) ||
    member.role?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleDelegate = async () => {
    if (!selectedMember || !item) return;
    setDelegating(true);
    try {
      await api.post('/team/delegate', {
        item_id: item.id,
        to_user_id: selectedMember.id,
        note: note
      });
      onDelegate(item.id, selectedMember, note);
      onClose();
    } catch {
      showToast("Failed to delegate item. Please try again.", "error");
    } finally {
      setDelegating(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose} aria-modal="true" role="dialog" aria-label="Delegate item">
      <div className="modal-content delegation-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-area">
            <Shield size={20} className="modal-icon" />
            <h2>Delegate Item</h2>
          </div>
          <button className="close-btn" onClick={onClose} aria-label="Close"><X size={20} /></button>
        </div>

        <div className="modal-body">
          <div className="delegation-item-summary">
            <span className="label">Item:</span>
            <span className="value">{item?.text}</span>
          </div>

          <div className="team-search">
            <Search size={18} className="search-icon" />
            <input 
              type="text" 
              placeholder="Search team members..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              autoFocus
              aria-label="Search team members"
            />
          </div>

          <div className="team-list" role="listbox" aria-label="Team members">
            {loadingMembers ? (
              <div className="loading-state" role="status">
                <Loader2 size={24} className="spin" />
                <p>Loading team...</p>
              </div>
            ) : filteredMembers.length > 0 ? (
              filteredMembers.map(member => (
                <div 
                  key={member.id} 
                  className={`team-member-card ${selectedMember?.id === member.id ? 'selected' : ''}`}
                  onClick={() => setSelectedMember(member)}
                  role="option"
                  aria-selected={selectedMember?.id === member.id}
                  tabIndex={0}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSelectedMember(member); } }}
                >
                  <div className="member-avatar">{member.avatar || member.username?.substring(0, 2).toUpperCase()}</div>
                  <div className="member-info">
                    <div className="member-name">{member.name || member.username}</div>
                    <div className="member-role">{member.role}</div>
                  </div>
                  <div className="member-status">
                    <div className={`status-badge ${member.availability?.toLowerCase().replace(' ', '-') || 'available'}`}>
                      {member.availability || 'Available'}
                    </div>
                    <div className="workload-indicator">
                      <Clock size={12} />
                      <span>{member.workload || 0} items</span>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-state" role="status">
                <p>No matching members found.</p>
              </div>
            )}
          </div>

          <div className="delegation-note">
            <label htmlFor="delegation-note">Add a note (optional)</label>
            <textarea 
              id="delegation-note"
              placeholder="Context for the team member..."
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose}>Cancel</button>
          <button 
            className="btn-primary" 
            disabled={!selectedMember || delegating}
            onClick={handleDelegate}
          >
            {delegating ? (
              <>
                <Loader2 size={18} className="spin" />
                <span>Delegating...</span>
              </>
            ) : (
              <>
                <Send size={18} />
                <span>Delegate to {selectedMember ? (selectedMember.name || selectedMember.username).split(' ')[0] : '...'}</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default DelegationModal;