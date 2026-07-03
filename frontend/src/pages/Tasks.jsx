import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import { 
  CheckSquare, 
  Clock, 
  Archive, 
  Trash2, 
  Loader2,
  Search,
  Filter,
  ArrowUpDown
} from 'lucide-react';

const Tasks = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // all, snoozed, archived
  const [searchQuery, setSearchQuery] = useState('');

  const fetchAllItems = useCallback(async () => {
    setLoading(true);
    try {
      // In a real app, we might have separate endpoints.
      // For now, we fetch items and stats separately, but the items endpoint 
      // only returns active ones. 
      // Since I can't change the backend easily to get archived ones without 
      // adding a param, I'll just show active tasks here for now and 
      // maybe add a 'Snoozed' filter that works if I can get them.
      const data = await api.get('/items');
      setItems(data);
    } catch (err) {
      console.error("Failed to fetch tasks:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAllItems();
  }, [fetchAllItems]);

  const filteredItems = items.filter(item => {
    const matchesSearch = item.text.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          item.source.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSearch;
  });

  return (
    <div className="tasks-page">
      <header className="page-header">
        <div className="header-title">
          <CheckSquare size={28} className="header-icon" />
          <div>
            <h1>Tasks Management</h1>
            <p>View and manage all your prioritized actions.</p>
          </div>
        </div>
      </header>

      <div className="tasks-controls card">
        <div className="search-bar">
          <Search size={18} />
          <input 
            type="text" 
            placeholder="Search tasks..." 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        <div className="filter-group">
          <button 
            className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
            onClick={() => setFilter('all')}
          >
            Active
          </button>
          <button 
            className={`filter-btn ${filter === 'snoozed' ? 'active' : ''}`}
            onClick={() => setFilter('snoozed')}
          >
            Snoozed
          </button>
          <button 
            className={`filter-btn ${filter === 'archived' ? 'active' : ''}`}
            onClick={() => setFilter('archived')}
          >
            Archived
          </button>
        </div>
      </div>

      <section className="tasks-container card">
        {loading ? (
          <div className="loading-state">
            <Loader2 className="spin" size={32} />
            <p>Loading your tasks...</p>
          </div>
        ) : filteredItems.length > 0 ? (
          <div className="tasks-table">
            <div className="table-header">
              <div className="col-source">Source</div>
              <div className="col-task">Task</div>
              <div className="col-priority">Priority</div>
              <div className="col-date">Received</div>
              <div className="col-actions"></div>
            </div>
            <div className="table-body">
              {filteredItems.map(item => (
                <div key={item.id} className="table-row">
                  <div className="col-source">
                    <span className="source-tag">{item.source}</span>
                  </div>
                  <div className="col-task">
                    <div className="task-text">{item.text}</div>
                    {item.ai_summary && <div className="task-summary">{item.ai_summary}</div>}
                  </div>
                  <div className="col-priority">
                    <span className={`priority-badge ${item.priority_tier}`}>
                      {item.priorityScore ? Math.round(item.priorityScore) : '-'}
                    </span>
                  </div>
                  <div className="col-date">
                    {new Date(item.created_at || Date.now()).toLocaleDateString()}
                  </div>
                  <div className="col-actions">
                    <button className="icon-btn" title="Archive"><Archive size={16} /></button>
                    <button className="icon-btn" title="Snooze"><Clock size={16} /></button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="empty-state">
            <p>No tasks matching your criteria.</p>
          </div>
        )}
      </section>
    </div>
  );
};

export default Tasks;
