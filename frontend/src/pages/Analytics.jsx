import { useState, useEffect } from 'react';
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
  Treemap
} from 'recharts';
import {
  Clock,
  Target,
  TrendingUp,
  AlertCircle,
  CheckCircle2,
  Zap,
  RefreshCw,
  Loader2
} from 'lucide-react';
import api from '../utils/api';

const MOCK_TREEMAP_DATA = [
  {
    name: 'Communications',
    children: [
      { name: 'Critical', value: 45, color: 'var(--priority-urgent)' },
      { name: 'High', value: 30, color: 'var(--priority-high)' },
      { name: 'Medium', value: 20, color: 'var(--priority-medium)' },
      { name: 'Low', value: 5, color: 'var(--priority-low)' },
    ],
  },
];

const MOCK_PRODUCTIVITY = [
  { day: '1', score: 65, baseline: 50 },
  { day: '5', score: 68, baseline: 50 },
  { day: '10', score: 75, baseline: 50 },
  { day: '15', score: 72, baseline: 50 },
  { day: '20', score: 82, baseline: 50 },
  { day: '25', score: 85, baseline: 50 },
  { day: '30', score: 88, baseline: 50 },
];

const CustomizedContent = (props) => {
  const { depth, x, y, width, height, index, colors, name } = props;

  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        style={{
          fill: depth < 2 ? colors[index % colors.length] : 'transparent',
          stroke: 'var(--color-paper-2)',
          strokeWidth: 2 / (depth + 1),
          strokeOpacity: 1 / (depth + 1),
        }}
      />
      {depth === 1 && width > 50 && height > 30 ? (
        <text x={x + width / 2} y={y + height / 2 + 7} textAnchor="middle" fill="var(--color-paper-2)" fontSize={width > 100 ? 14 : 10} fontWeight="bold">
          {name}
        </text>
      ) : null}
    </g>
  );
};

const KPICard = ({ title, value, icon: Icon, trend, colorClass, delay }) => (
  <div className="card glass-effect kpi-card animate-in" style={{ animationDelay: `${delay}ms` }}>
    <div className="kpi-header">
      <div className={`kpi-icon ${colorClass}`}>
        <Icon size={24} />
      </div>
      <div className="kpi-trend positive">
        <TrendingUp size={14} />
        <span>{trend}%</span>
      </div>
    </div>
    <div className="kpi-content">
      <h3 className="kpi-title">{title}</h3>
      <p className="kpi-value">{value}</p>
    </div>
  </div>
);

const Analytics = () => {
  const [dateRange, setDateRange] = useState('7d');
  const [isLive, setIsLive] = useState(false);
  const [loading, setLoading] = useState(true);
  const [metrics, setMetrics] = useState(null);
  const [selectedTier, setSelectedTier] = useState(null);

  const fetchMetrics = async () => {
    try {
      const data = await api.get('/analytics/metrics');
      setMetrics(data);
    } catch (err) {
      console.error("Failed to fetch metrics:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    if (isLive) {
      const interval = setInterval(fetchMetrics, 5000);
      return () => clearInterval(interval);
    }
  }, [isLive]);

  const onTreemapClick = (node) => {
    if (node && node.name) {
      setSelectedTier(node.name === selectedTier ? null : node.name);
    }
  };

  if (loading && !metrics) {
    return (
      <div className="loading-container">
        <Loader2 size={48} className="spin" />
        <p>Loading Enterprise Analytics...</p>
      </div>
    );
  }

  // Format data for charts
  const priorityData = metrics ? [
    {
      name: 'Communications',
      children: [
        { name: 'Urgent', value: metrics.priority_distribution.urgent, color: 'var(--priority-urgent)' },
        { name: 'High', value: metrics.priority_distribution.high, color: 'var(--priority-high)' },
        { name: 'Medium', value: metrics.priority_distribution.medium, color: 'var(--priority-medium)' },
        { name: 'Low', value: metrics.priority_distribution.low, color: 'var(--priority-low)' },
      ],
    }
  ] : MOCK_TREEMAP_DATA;

  const activityData = metrics?.activity_trends || MOCK_PRODUCTIVITY;

  return (
    <div className="analytics-container">
      <header className="analytics-header">
        <div className="header-main">
          <h1>Enterprise Analytics v2</h1>
          <p className="subtitle">Real-time productivity insights for your team</p>
        </div>
        <div className="header-actions">
          <div className="view-toggle glass">
            <button 
              className={`toggle-btn ${dateRange === '7d' ? 'active' : ''}`}
              onClick={() => setDateRange('7d')}
            >
              7 Days
            </button>
            <button 
              className={`toggle-btn ${dateRange === '30d' ? 'active' : ''}`}
              onClick={() => setDateRange('30d')}
            >
              30 Days
            </button>
          </div>
          <button 
            className={`live-btn glass ${isLive ? 'active' : ''}`}
            onClick={() => setIsLive(!isLive)}
          >
            <RefreshCw size={16} className={isLive ? 'spin' : ''} />
            <span>{isLive ? 'Live Mode' : 'Static View'}</span>
          </button>
        </div>
      </header>

      <div className="kpi-grid">
        <KPICard 
          title="Avg. Time to Action" 
          value={`${Math.round(metrics?.average_time_to_action_seconds / 60 || 0)}m`} 
          icon={Clock} 
          trend="18" 
          colorClass="text-blue"
          delay={0}
        />
        <KPICard 
          title="Team Focus Score" 
          value={`${Math.round(metrics?.team_focus_score || 0)}/100`} 
          icon={Target} 
          trend="12" 
          colorClass="text-purple"
          delay={100}
        />
        <KPICard 
          title="Items Processed" 
          value={metrics?.total_items_processed || 0} 
          icon={Zap} 
          trend="15" 
          colorClass="text-yellow"
          delay={200}
        />
        <KPICard 
          title="Actions Taken" 
          value={metrics?.total_actions_taken || 0} 
          icon={CheckCircle2} 
          trend="2" 
          colorClass="text-green"
          delay={300}
        />
      </div>

      <div className="analytics-grid">
        <div className="card glass-effect chart-container wide interactive-chart">
          <div className="chart-header">
            <div className="header-with-badge">
              <h3>Activity Trends</h3>
              {selectedTier && <span className={`priority-badge ${selectedTier.toLowerCase()}`}>{selectedTier}</span>}
            </div>
            <p>Daily volume of administrative and user actions</p>
          </div>
          <div style={{ width: '100%', height: 350 }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={activityData}>
                <defs>
                  <linearGradient id="colorActions" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="var(--color-accent)" stopOpacity={0.25}/>
                    <stop offset="95%" stopColor="var(--color-accent)" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-rule)" vertical={false} />
                <XAxis dataKey="date" stroke="var(--color-ink-3)" axisLine={false} tickLine={false} />
                <YAxis stroke="var(--color-ink-3)" axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ backgroundColor: 'var(--color-paper-2)', border: '1px solid var(--color-rule)', borderRadius: '12px' }}
                />
                <Area
                  type="monotone"
                  dataKey="actions"
                  stroke="var(--color-accent)"
                  strokeWidth={3}
                  fillOpacity={1}
                  fill="url(#colorActions)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card glass-effect chart-container">
          <div className="chart-header">
            <h3>Priority Distribution</h3>
            <p>Hierarchy of urgency across all team items</p>
          </div>
          <div style={{ width: '100%', height: 300 }}>
            <ResponsiveContainer width="100%" height="100%">
              <Treemap
                data={priorityData}
                dataKey="value"
                aspectRatio={4 / 3}
                stroke="var(--color-paper-2)"
                fill="var(--color-accent)"
                onClick={onTreemapClick}
                content={<CustomizedContent colors={['var(--priority-urgent)', 'var(--priority-high)', 'var(--priority-medium)', 'var(--priority-low)']} />}
              />
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card glass-effect chart-container wide">
          <div className="chart-header">
            <h3>Recent Critical Insights</h3>
          </div>
          <div className="insights-list">
            <div className="insight-item highlight">
              <div className="insight-icon yellow">
                <AlertCircle size={18} />
              </div>
              <div className="insight-text">
                <p><strong>System Performance:</strong> Average time to action is {Math.round(metrics?.average_time_to_action_seconds / 60 || 0)} minutes, which is within the target SLA of 30 minutes.</p>
              </div>
            </div>
            <div className="insight-item highlight">
              <div className="insight-icon green">
                <CheckCircle2 size={18} />
              </div>
              <div className="insight-text">
                <p><strong>Team Alignment:</strong> The Focus Score is {Math.round(metrics?.team_focus_score || 0)}%, indicating strong adherence to AI-prioritized critical tasks.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Analytics;
