import { useNavigate } from 'react-router-dom';
import ThemeToggle from '../components/ThemeToggle';
import LiquidButton from '../components/LiquidButton';
import SourceLogo from '../components/SourceLogo';
import { INTEGRATIONS } from '../constants/integrations';
import { CheckCircle2, ArrowRight, Zap, Layers, Target, Shield } from 'lucide-react';

const FeatureCard = ({ icon: Icon, title, description }) => (
  <div className="feature-card"><div className="icon"><Icon size={24} /></div><h3>{title}</h3><p className="text-body" style={{ color: 'var(--color-ink-2)' }}>{description}</p></div>
);

const PricingCard = ({ tier, price, features, cta, isFree, onClick }) => (
  <div className="pricing-card">
    <div className="tier">{tier}</div>
    <div className="price">{isFree ? <span style={{ fontSize: '36px', fontWeight: 700 }}>Free</span> : price === 'Custom' ? <span style={{ fontSize: '28px', fontWeight: 700 }}>Custom</span> : <><span className="currency">$</span><span className="amount">{price}</span><span className="period">/mo</span></>}</div>
    <ul>{features.map((f, i) => (<li key={i}><CheckCircle2 size={16} className="check-icon" />{f}</li>))}</ul>
    <button className="btn btn-secondary" style={{ marginTop: 'auto' }} onClick={onClick}>{cta}</button>
  </div>
);

const IntegrationIcon = ({ id, label }) => (
  <div className="integration-chip">
    <SourceLogo source={id} size={20} />
    <span>{label}</span>
  </div>
);

const GitHubIcon = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"/></svg>;

const TwitterIcon = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 4l11.733 16h4.267l-11.733 -16z"/><path d="M4 20l6.768 -6.768m2.46 -2.46L20 4"/></svg>;

const LinkedInIcon = () => <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 8a6 6 0 0 1 6 6v7h-4v-7a2 2 0 0 0-2-2 2 2 0 0 0-2 2v7h-4v-7a6 6 0 0 1 6-6z"/><rect width="4" height="12" x="2" y="9"/><circle cx="4" cy="4" r="2"/></svg>;

export default function LandingPage() {
  const navigate = useNavigate();
  const scrollTo = (id) => {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };
  return (
    <div className="landing-container">
      <nav className="landing-nav">
        <div className="logo"><div className="logo-icon">C</div><span className="logo-text">Clutsch</span></div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <ThemeToggle variant="icon" />
          <button onClick={() => scrollTo('features')} className="btn btn-ghost btn-sm">Features</button>
          <button onClick={() => scrollTo('pricing')} className="btn btn-ghost btn-sm">Pricing</button>
          <button onClick={() => navigate('/login')} className="btn btn-secondary btn-sm">Login</button>
          <button onClick={() => navigate('/login?mode=signup')} className="btn btn-primary btn-sm">Get Started</button>
        </div>
      </nav>

      <section className="landing-hero">
        <div className="hero-content">
          <div className="chip chip-accent" style={{ width: 'fit-content' }}><Zap size={14} /> Now with AI-Powered Prioritization</div>
          <h1 className="text-display-xl" style={{ color: 'var(--color-ink)' }}>Clear the Noise.<br />Focus on What Matters.</h1>
          <p className="text-body-l" style={{ color: 'var(--color-ink-2)', maxWidth: '480px' }}>Clutsch aggregates your emails, Slack messages, and tasks, then uses AI to rank them by urgency.</p>
          <div className="hero-actions">
            <LiquidButton onClick={() => navigate('/login?mode=signup')}>Start Free Trial <ArrowRight size={18} /></LiquidButton>
            <p className="text-caption" style={{ color: 'var(--color-ink-3)' }}>No credit card required. 14-day free trial.</p>
          </div>
        </div>
        <div className="hero-visual">
          <div className="card" style={{ padding: '12px', transform: 'perspective(1000px) rotateY(-3deg)', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.15)' }}>
            <svg width="100%" height="320" viewBox="0 0 520 320" style={{ borderRadius: '8px' }}>
              <rect width="520" height="320" rx="8" fill="#FAFAF9"/>
              <rect x="0" y="0" width="100" height="320" rx="8" fill="#FFF" stroke="#EAE8E4" strokeWidth="1"/>
              <rect x="16" y="20" width="28" height="28" rx="6" fill="#4A4743"/>
              <rect x="52" y="27" width="36" height="6" rx="3" fill="#1C1B1A" opacity="0.3"/>
              <rect x="16" y="68" width="68" height="8" rx="4" fill="#F5F4F2"/>
              <rect x="16" y="88" width="68" height="8" rx="4" fill="#F5F4F2"/>
              <rect x="116" y="0" width="404" height="56" fill="#FFF"/>
              <rect x="128" y="72" width="180" height="100" rx="12" fill="#FFF" stroke="#EAE8E4" strokeWidth="1"/>
              <circle cx="148" cy="110" r="16" fill="#F5F4F2"/>
              <rect x="170" y="96" width="80" height="6" rx="3" fill="#1C1B1A" opacity="0.6"/>
              <rect x="128" y="188" width="180" height="100" rx="12" fill="#FFF" stroke="#EAE8E4" strokeWidth="1"/>
              <circle cx="148" cy="226" r="16" fill="#F5F4F2"/>
              <circle cx="276" cy="110" r="12" fill="#E8434F"/>
              <circle cx="276" cy="226" r="12" fill="#F5B826"/>
              <rect x="320" y="72" width="188" height="100" rx="12" fill="#FFF" stroke="#EAE8E4" strokeWidth="1"/>
              <rect x="336" y="88" width="60" height="30" rx="6" fill="#F5F4F2"/>
              <rect x="320" y="188" width="188" height="100" rx="12" fill="#FFF" stroke="#EAE8E4" strokeWidth="1"/>
            </svg>
          </div>
        </div>
      </section>

      <section style={{ padding: '60px 0', textAlign: 'center' }}>
        <p className="text-caption" style={{ color: 'var(--color-ink-3)', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600, marginBottom: '24px' }}>Works with your favorite tools</p>
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: '12px' }}>
          {/* Driven by the shared list so this strip can never advertise an
              integration the product doesn't actually have. */}
          {INTEGRATIONS.map(({ id, name }) => (
            <IntegrationIcon key={id} id={id} label={name} />
          ))}
        </div>
      </section>

      <section id="features" className="landing-section" style={{ padding: '80px 0' }}>
        <div className="section-header-centered">
          <h2>Everything you need to master your day</h2>
          <p className="text-body-l" style={{ color: 'var(--color-ink-2)' }}>Bring all your communications into a single, intelligent workflow.</p>
        </div>
        <div className="features-grid">
          <FeatureCard icon={Layers} title="Unified Intelligence" description="Connect Gmail, Slack, Jira, and more. See all your high-priority items in one place." />
          <FeatureCard icon={Target} title="AI Scoring Engine" description="Analyzes sender importance, deadlines, and content urgency to score every item 0-100." />
          <FeatureCard icon={Shield} title="Enterprise Privacy" description="DPDP compliant. Your data is encrypted and used only to power your own prioritization." />
        </div>
      </section>

      <section id="pricing" className="landing-section" style={{ padding: '80px 0', background: 'var(--color-paper-3)' }}>
        <div className="section-header-centered">
          <h2>Simple, transparent pricing</h2>
          <p className="text-body-l" style={{ color: 'var(--color-ink-2)' }}>Choose the plan that fits your scale.</p>
        </div>
        <div className="pricing-grid">
          <PricingCard tier="Free" isFree cta="Get Started Free" features={["2 Integrations", "50 Messages/mo", "AI Priority Scoring", "Basic Support"]} onClick={() => navigate('/login?mode=signup')} />
          <PricingCard tier="Pro" price="12" cta="Get Pro" features={["All Integrations", "Unlimited Messages", "AI Priority Scoring", "Quick Actions", "Advanced Search", "Mobile Access"]} onClick={() => navigate('/login?mode=signup')} />
          <PricingCard tier="SME" price="Custom" cta="Contact Sales" features={["Everything in Pro", "Up to 20 Users", "Team Shared Feeds", "Delegation Workflow", "Priority Support"]} onClick={() => navigate('/login?mode=signup')} />
          <PricingCard tier="Enterprise" price="Custom" cta="Contact Sales" features={["Everything in SME", "Unlimited Users", "Custom Integrations", "SAML / SSO", "Dedicated Manager", "Analytics"]} onClick={() => navigate('/login?mode=signup')} />
        </div>
      </section>

      <footer style={{ padding: '60px 0 40px', borderTop: '1px solid var(--color-rule)' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: '40px', marginBottom: '40px' }}>
          <div style={{ maxWidth: '300px' }}>
            <div className="logo" style={{ marginBottom: '16px' }}><div className="logo-icon">C</div><span className="logo-text">Clutsch</span></div>
            <p className="text-body" style={{ color: 'var(--color-ink-3)' }}>AI-powered prioritization for busy professionals.</p>
          </div>
          <div style={{ display: 'flex', gap: '60px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <h5 className="text-label" style={{ color: 'var(--color-ink)' }}>Product</h5>
              <button onClick={() => scrollTo('features')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-ink-3)', fontSize: '15px', textAlign: 'left', padding: 0, fontFamily: 'var(--font-body)' }}>Features</button>
              <button onClick={() => scrollTo('pricing')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-ink-3)', fontSize: '15px', textAlign: 'left', padding: 0, fontFamily: 'var(--font-body)' }}>Pricing</button>
              <button onClick={() => navigate('/login')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-ink-3)', fontSize: '15px', textAlign: 'left', padding: 0, fontFamily: 'var(--font-body)' }}>Integrations</button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <h5 className="text-label" style={{ color: 'var(--color-ink)' }}>Company</h5>
              <button onClick={() => navigate('/login')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-ink-3)', fontSize: '15px', textAlign: 'left', padding: 0, fontFamily: 'var(--font-body)' }}>About</button>
              <button onClick={() => navigate('/login')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-ink-3)', fontSize: '15px', textAlign: 'left', padding: 0, fontFamily: 'var(--font-body)' }}>Blog</button>
              <button onClick={() => navigate('/login')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-ink-3)', fontSize: '15px', textAlign: 'left', padding: 0, fontFamily: 'var(--font-body)' }}>Contact</button>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <h5 className="text-label" style={{ color: 'var(--color-ink)' }}>Legal</h5>
              <button onClick={() => navigate('/login')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-ink-3)', fontSize: '15px', textAlign: 'left', padding: 0, fontFamily: 'var(--font-body)' }}>Privacy Policy</button>
              <button onClick={() => navigate('/login')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-ink-3)', fontSize: '15px', textAlign: 'left', padding: 0, fontFamily: 'var(--font-body)' }}>Terms of Service</button>
              <button onClick={() => navigate('/login')} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-ink-3)', fontSize: '15px', textAlign: 'left', padding: 0, fontFamily: 'var(--font-body)' }}>Cookie Policy</button>
            </div>
          </div>
        </div>
        <div style={{ borderTop: '1px solid var(--color-rule)', paddingTop: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <p className="text-caption" style={{ color: 'var(--color-ink-3)' }}>&copy; 2026 Clutsch. All rights reserved.</p>
          <div style={{ display: 'flex', gap: '16px' }}>
            <a className="btn btn-ghost btn-sm" style={{ padding: '8px' }}><GitHubIcon /></a>
            <a className="btn btn-ghost btn-sm" style={{ padding: '8px' }}><TwitterIcon /></a>
            <a className="btn btn-ghost btn-sm" style={{ padding: '8px' }}><LinkedInIcon /></a>
          </div>
        </div>
      </footer>
    </div>
  );
}