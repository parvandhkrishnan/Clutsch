import React from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  CheckCircle2, 
  ArrowRight, 
  MessageSquare, 
  Mail, 
  MessageCircle, 
  LayoutGrid, 
  Zap, 
  Shield, 
  Layers, 
  Users,
  Target,
  Rocket
} from 'lucide-react';
import heroImage from '../assets/hero.png';

const FeatureCard = ({ icon: Icon, title, description }) => (
  <div className="landing-feature-card glass">
    <div className="feature-icon-container">
      <Icon size={24} className="feature-icon" />
    </div>
    <h3>{title}</h3>
    <p>{description}</p>
  </div>
);

const IntegrationIcon = ({ icon: Icon, label }) => (
  <div className="integration-chip glass">
    <Icon size={18} />
    <span>{label}</span>
  </div>
);

const PricingCard = ({ tier, price, features, highlighted, cta }) => (
  <div className={`pricing-card glass ${highlighted ? 'highlighted' : ''}`}>
    <div className="pricing-header">
      <h4>{tier}</h4>
      <div className="price">
        <span className="currency">$</span>
        <span className="amount">{price}</span>
        {price !== 'Custom' && <span className="period">/mo</span>}
      </div>
    </div>
    <ul className="pricing-features">
      {features.map((feature, i) => (
        <li key={i}>
          <CheckCircle2 size={16} className="check-icon" />
          <span>{feature}</span>
        </li>
      ))}
    </ul>
    <button className={`btn ${highlighted ? 'btn-primary' : 'btn-secondary'}`}>
      {cta}
    </button>
  </div>
);

const LandingPage = () => {
  const navigate = useNavigate();

  return (
    <div className="landing-container">
      <nav className="landing-nav">
        <div className="logo">
          <div className="logo-icon">P</div>
          <span className="logo-text">PriorityFlow</span>
        </div>
        <div className="nav-actions">
          <button onClick={() => navigate('/login')} className="btn btn-secondary btn-sm">Login</button>
          <button onClick={() => navigate('/login')} className="btn btn-primary btn-sm">Get Started</button>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="landing-hero">
        <div className="hero-content">
          <div className="badge-announcement">
            <Zap size={14} />
            <span>Now with AI-Powered Prioritization</span>
          </div>
          <h1>Clear the Noise. <br /><span className="text-gradient">Focus on High-Impact.</span></h1>
          <p className="hero-description">
            The unified dashboard for busy professionals. PriorityFlow aggregates your emails, Slack messages, 
            and tasks, then uses AI to rank them by urgency and importance.
          </p>
          <div className="hero-actions">
            <button onClick={() => navigate('/login')} className="btn btn-primary btn-lg">
              Start Free Trial <ArrowRight size={18} />
            </button>
            <p className="hero-note">No credit card required. 14-day free trial.</p>
          </div>
        </div>
        <div className="hero-visual">
          <div className="hero-image-container glass">
            <img src={heroImage} alt="PriorityFlow Dashboard Mockup" />
          </div>
        </div>
      </section>

      {/* Integrations Section */}
      <section className="landing-integrations">
        <p className="section-subtitle">Trusted by leaders across every platform</p>
        <div className="integrations-scroll">
          <IntegrationIcon icon={Mail} label="Gmail" />
          <IntegrationIcon icon={MessageCircle} label="Slack" />
          <IntegrationIcon icon={LayoutGrid} label="Jira" />
          <IntegrationIcon icon={Users} label="Teams" />
          <IntegrationIcon icon={MessageSquare} label="WhatsApp" />
          <IntegrationIcon icon={Rocket} label="Linear" />
        </div>
      </section>

      {/* Features Section */}
      <section className="landing-features">
        <div className="section-header-centered">
          <h2>Everything you need to <span className="text-gradient">master your day</span></h2>
          <p>Ditch the tab-switching. Bring all your communications into a single, intelligent workflow.</p>
        </div>
        <div className="features-grid">
          <FeatureCard 
            icon={Layers}
            title="Unified Intelligence"
            description="Connect Gmail, Slack, Jira, and more. See all your high-priority items in one place without the context switching."
          />
          <FeatureCard 
            icon={Target}
            title="AI Scoring Engine"
            description="Our advanced model analyzes sender importance, deadlines, and content urgency to give every item a 0-100 priority score."
          />
          <FeatureCard 
            icon={Zap}
            title="Action-Oriented"
            description="Archive, snooze, or reply directly from the feed. Designed for rapid triage so you can get back to deep work."
          />
          <FeatureCard 
            icon={Shield}
            title="Enterprise Privacy"
            description="DPDP compliant and SOC2 ready. Your data is encrypted and used only to power your own prioritization."
          />
        </div>
      </section>

      {/* Pricing Section */}
      <section className="landing-pricing">
        <div className="section-header-centered">
          <h2>Simple, transparent <span className="text-gradient">pricing</span></h2>
          <p>Choose the plan that fits your scale.</p>
        </div>
        <div className="pricing-grid">
          <PricingCard 
            tier="Pro"
            price="19"
            cta="Get Started"
            features={[
              "All Standard Integrations",
              "AI Priority Scoring",
              "Quick Actions (Snooze/Archive)",
              "Basic Search & Filtering",
              "Mobile Access"
            ]}
          />
          <PricingCard 
            tier="Enterprise"
            price="Custom"
            cta="Contact Sales"
            highlighted={true}
            features={[
              "Everything in Pro",
              "Shared Team Feeds",
              "Delegation Workflow",
              "Custom Priority Logic",
              "SAML / SSO",
              "Dedicated Account Manager"
            ]}
          />
        </div>
      </section>

      {/* Footer */}
      <footer className="landing-footer">
        <div className="footer-content">
          <div className="footer-brand">
            <div className="logo">
              <div className="logo-icon">P</div>
              <span className="logo-text">PriorityFlow</span>
            </div>
            <p>Mastering your focus, one priority at a time.</p>
          </div>
          <div className="footer-links">
            <div className="footer-col">
              <h5>Product</h5>
              <a href="#">Features</a>
              <a href="#">Integrations</a>
              <a href="#">Pricing</a>
            </div>
            <div className="footer-col">
              <h5>Company</h5>
              <a href="#">About</a>
              <a href="#">Privacy</a>
              <a href="#">Terms</a>
            </div>
          </div>
        </div>
        <div className="footer-bottom">
          <p>&copy; 2026 PriorityFlow Inc. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
