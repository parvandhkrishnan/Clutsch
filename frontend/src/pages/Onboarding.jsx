import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import api from '../utils/api';
import IntegrationModal from '../components/IntegrationModal';
import { 
  Mail, 
  MessageCircle, 
  ArrowRight, 
  CheckCircle2, 
  Loader2, 
  Zap,
  Target,
  Users
} from 'lucide-react';

const Onboarding = () => {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [integrations, setIntegrations] = useState([]);
  const [selectedIntegration, setSelectedIntegration] = useState(null);
  const [isConnectModalOpen, setIsConnectModalOpen] = useState(false);
  const [syncStatus, setSyncStatus] = useState('idle');

  const fetchIntegrations = async () => {
    try {
      const data = await api.get('/integrations');
      setIntegrations(data.connected || []);
    } catch (err) {
      console.error("Failed to fetch integrations", err);
    }
  };

  useEffect(() => {
    fetchIntegrations();
  }, []);

  const handleNext = () => setStep(prev => prev + 1);

  const handleConnectSuccess = async (id) => {
    await api.post(`/integrations/${id}/connect`, { token: 'dummy-token' });
    await fetchIntegrations();
    setIsConnectModalOpen(false);
    setSyncStatus('syncing');
    setStep(3);
    setTimeout(() => {
      setSyncStatus('complete');
    }, 3000);
  };

  const dotStyle = (i) => ({
    width: '10px',
    height: '10px',
    borderRadius: '50%',
    background: step > i ? 'var(--accent)' : step === i ? 'var(--accent)' : 'var(--border)',
    transition: 'all 200ms ease-out',
    opacity: step === i ? 1 : 0.5,
  });

  const WelcomeStep = () => (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '24px', textAlign: 'center', padding: '40px 0', animation: 'fadeIn 250ms ease-out' }}>
      <div style={{ width: '80px', height: '80px', borderRadius: 'var(--radius-lg)', background: 'var(--accent-soft)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Zap size={40} style={{ color: 'var(--accent)' }} />
      </div>
      <h1 style={{ fontSize: '28px' }}>Welcome to Clutsch</h1>
      <p className="text-body-l" style={{ color: 'var(--text-secondary)', maxWidth: '440px' }}>
        Let's clear the noise. We'll help you focus on high-impact work by aggregating and prioritizing your communications.
      </p>
      <button className="btn btn-primary btn-lg" onClick={handleNext}>
        Get Started <ArrowRight size={18} />
      </button>
    </div>
  );

  const IntegrationStep = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', animation: 'fadeIn 250ms ease-out' }}>
      <div style={{ textAlign: 'center' }}>
        <h2 style={{ marginBottom: '8px' }}>Connect a Source</h2>
        <p className="text-body" style={{ color: 'var(--text-secondary)' }}>Choose your primary communication channel to begin prioritization.</p>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', maxWidth: '480px', margin: '0 auto' }}>
        {[
          { id: 'gmail', name: 'Gmail', icon: Mail },
          { id: 'slack', name: 'Slack', icon: MessageCircle },
        ].map((item) => {
          const isConnected = integrations.includes(item.id);
          const Icon = item.icon;
          return (
            <div key={item.id}
              onClick={() => {
                setSelectedIntegration({ id: item.id, name: item.name, icon: Icon });
                setIsConnectModalOpen(true);
              }}
              style={{ 
                padding: '24px', 
                background: isConnected ? 'var(--accent-soft)' : 'var(--bg-surface)',
                border: `1px solid ${isConnected ? 'var(--accent-border)' : 'var(--border)'}`,
                borderRadius: 'var(--radius-lg)',
                display: 'flex', 
                flexDirection: 'column', 
                alignItems: 'center', 
                gap: '12px',
                cursor: 'pointer',
                transition: 'all 200ms ease-out',
              }}
            >
              <div style={{ width: '56px', height: '56px', borderRadius: 'var(--radius-md)', background: isConnected ? 'var(--accent)' : 'var(--bg-subtle)', color: isConnected ? '#fff' : 'var(--text-secondary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Icon size={28} />
              </div>
              <h3 style={{ fontSize: '16px' }}>{item.name}</h3>
              {isConnected ? (
                <div className="chip chip-accent"><CheckCircle2 size={12} /> Connected</div>
              ) : (
                <button className="btn btn-secondary btn-sm">Connect</button>
              )}
            </div>
          );
        })}
      </div>
      <div style={{ textAlign: 'center' }}>
        <button className="btn btn-ghost" onClick={handleNext}>I'll do this later</button>
      </div>
    </div>
  );

  const SurveyStep = () => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', animation: 'fadeIn 250ms ease-out' }}>
      <div style={{ textAlign: 'center' }}>
        <h2 style={{ marginBottom: '8px' }}>Tune Your AI</h2>
        <p className="text-body" style={{ color: 'var(--text-secondary)' }}>Help us understand what matters most to you.</p>
      </div>
      <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '20px', maxWidth: '480px', margin: '0 auto' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <label className="text-label" style={{ color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}><Target size={16} /> Key stakeholders</label>
          <input type="text" placeholder="e.g. CEO, Key Clients, Project Alpha Team" />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <label className="text-label" style={{ color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}><Zap size={16} /> Primary focus this week</label>
          <input type="text" placeholder="e.g. Q3 Planning, Bug Triage, Client Onboarding" />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <label className="text-label" style={{ color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}><Users size={16} /> Top collaborators</label>
          <input type="text" placeholder="e.g. Jane (Product), Mike (Backend)" />
        </div>
      </div>
      <div style={{ textAlign: 'center' }}>
        <button className="btn btn-primary" onClick={handleNext}>Save & Continue</button>
      </div>
    </div>
  );

  const SyncStep = () => (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '24px', textAlign: 'center', padding: '40px 0', animation: 'fadeIn 250ms ease-out' }}>
      {syncStatus === 'syncing' ? (
        <>
          <div style={{ width: '80px', height: '80px', borderRadius: 'var(--radius-lg)', background: 'var(--accent-soft)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Loader2 size={40} style={{ color: 'var(--accent)', animation: 'spin 1s linear infinite' }} />
          </div>
          <h2 style={{ fontSize: '24px' }}>Fetching & Prioritizing...</h2>
          <p className="text-body" style={{ color: 'var(--text-secondary)' }}>Our AI is analyzing your communications to build your first focus moment.</p>
        </>
      ) : (
        <>
          <div style={{ width: '80px', height: '80px', borderRadius: 'var(--radius-lg)', background: '#F0FDF4', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <CheckCircle2 size={40} style={{ color: 'var(--success)' }} />
          </div>
          <h2 style={{ fontSize: '24px' }}>You're Ready to Focus</h2>
          <p className="text-body" style={{ color: 'var(--text-secondary)' }}>We've identified 12 high-priority items that need your attention.</p>
          <button className="btn btn-primary btn-lg" onClick={() => navigate('/dashboard?tour=true')}>
            Start Focusing <ArrowRight size={18} />
          </button>
        </>
      )}
    </div>
  );

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px', background: 'var(--bg-canvas)' }}>
      <div className="card" style={{ maxWidth: '600px', width: '100%', padding: '40px' }}>
        {/* Progress dots */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: '8px', marginBottom: '32px' }}>
          {[0, 1, 2, 3].map(i => <div key={i} style={dotStyle(i)} />)}
        </div>

        {step === 0 && <WelcomeStep />}
        {step === 1 && <IntegrationStep />}
        {step === 2 && <SurveyStep />}
        {step === 3 && <SyncStep />}
      </div>

      {selectedIntegration && (
        <IntegrationModal 
          isOpen={isConnectModalOpen}
          onClose={() => setIsConnectModalOpen(false)}
          integration={selectedIntegration}
          onConnectSuccess={handleConnectSuccess}
        />
      )}
    </div>
  );
};

export default Onboarding;