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
  const [step, setStep] = useState(0); // 0: Welcome, 1: Integrations, 2: Survey, 3: Success/Sync
  const [integrations, setIntegrations] = useState([]);
  const [selectedIntegration, setSelectedIntegration] = useState(null);
  const [isConnectModalOpen, setIsConnectModalOpen] = useState(false);
  const [syncStatus, setSyncStatus] = useState('idle'); // idle, syncing, complete

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
    
    // Simulate sync time
    setTimeout(() => {
      setSyncStatus('complete');
    }, 3000);
  };

  const WelcomeStep = () => (
    <div className="onboarding-step welcome-step animate-in">
      <div className="onboarding-icon-main">
        <Zap size={64} className="text-primary-blue" />
      </div>
      <h1>Welcome to PriorityFlow</h1>
      <p className="hero-description">
        Let's clear the noise. We'll help you focus on high-impact work by aggregating and prioritizing your communications.
      </p>
      <button className="btn btn-primary btn-large" onClick={handleNext}>
        <span>Get Started</span>
        <ArrowRight size={20} />
      </button>
    </div>
  );

  const IntegrationStep = () => (
    <div className="onboarding-step integration-step animate-in">
      <h2>Connect a Source</h2>
      <p className="subtitle">Choose your primary communication channel to begin prioritization.</p>
      
      <div className="onboarding-integrations-grid">
        <div 
          className={`onboarding-integration-card ${integrations.includes('gmail') ? 'connected' : ''}`}
          onClick={() => {
            setSelectedIntegration({ id: 'gmail', name: 'Gmail', icon: Mail });
            setIsConnectModalOpen(true);
          }}
        >
          <div className="integration-icon-bg"><Mail size={32} /></div>
          <h3>Gmail</h3>
          {integrations.includes('gmail') ? <CheckCircle2 className="text-success" /> : <button className="btn-sm">Connect</button>}
        </div>
        
        <div 
          className={`onboarding-integration-card ${integrations.includes('slack') ? 'connected' : ''}`}
          onClick={() => {
            setSelectedIntegration({ id: 'slack', name: 'Slack', icon: MessageCircle });
            setIsConnectModalOpen(true);
          }}
        >
          <div className="integration-icon-bg"><MessageCircle size={32} /></div>
          <h3>Slack</h3>
          {integrations.includes('slack') ? <CheckCircle2 className="text-success" /> : <button className="btn-sm">Connect</button>}
        </div>
      </div>
      
      <div className="onboarding-footer-actions">
        <button className="btn-text" onClick={handleNext}>I'll do this later</button>
      </div>
    </div>
  );

  const SurveyStep = () => (
    <div className="onboarding-step survey-step animate-in">
      <h2>Tune Your AI</h2>
      <p className="subtitle">Help us understand what matters most to you today.</p>
      
      <div className="survey-form card glass">
        <div className="survey-question">
          <label><Target size={18} /> Who are your most important stakeholders?</label>
          <input type="text" placeholder="e.g. CEO, Key Clients, Project Alpha Team" />
        </div>
        
        <div className="survey-question">
          <label><Zap size={18} /> What's your primary focus this week?</label>
          <input type="text" placeholder="e.g. Q3 Planning, Bug Triage, Client Onboarding" />
        </div>
        
        <div className="survey-question">
          <label><Users size={18} /> Which team members do you collaborate with most?</label>
          <input type="text" placeholder="e.g. Jane (Product), Mike (Backend)" />
        </div>
      </div>
      
      <button className="btn btn-primary" onClick={handleNext}>
        Save & Continue
      </button>
    </div>
  );

  const SyncStep = () => (
    <div className="onboarding-step sync-step animate-in">
      {syncStatus === 'syncing' ? (
        <>
          <Loader2 size={64} className="spin text-primary-blue" />
          <h2>Fetching & Prioritizing...</h2>
          <p>Our AI is analyzing your communications to build your first focus moment.</p>
        </>
      ) : (
        <>
          <div className="success-icon-bg">
            <CheckCircle2 size={64} className="text-success" />
          </div>
          <h2>You're Ready to Focus</h2>
          <p>We've identified 12 high-priority items that need your attention.</p>
          <button className="btn btn-primary btn-large" onClick={() => navigate('/dashboard?tour=true')}>
            Start Focusing
          </button>
        </>
      )}
    </div>
  );

  return (
    <div className="onboarding-container landing-container">
      <div className="onboarding-content glass">
        <div className="onboarding-progress">
          {[0, 1, 2, 3].map(i => (
            <div key={i} className={`progress-dot ${step === i ? 'active' : ''} ${step > i ? 'complete' : ''}`} />
          ))}
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
