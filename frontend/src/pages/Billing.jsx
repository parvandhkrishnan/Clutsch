import React, { useState } from 'react';
import { 
  Check, 
  Zap, 
  Users, 
  CreditCard, 
  Download, 
  ShieldCheck, 
  ArrowRight,
  TrendingUp,
  Loader2
} from 'lucide-react';
import api from '../utils/api';
import { showToast } from '../utils/toast';

const PlanCard = ({ title, price, features, highlighted, cta, isCustom, current, onUpgrade, loading }) => (
  <div className={`card billing-plan-card glass-effect ${highlighted ? 'enterprise-highlight' : ''}`}>
    {highlighted && <div className="enterprise-badge">RECOMMENDED</div>}
    <div className="plan-header">
      <h3>{title}</h3>
      <div className="plan-price">
        {isCustom ? (
          <span className="amount">Custom</span>
        ) : (
          <>
            <span className="currency">$</span>
            <span className="amount">{price}</span>
            <span className="period">/mo</span>
          </>
        )}
      </div>
    </div>
    <ul className="plan-features">
      {features.map((feature, i) => (
        <li key={i}>
          <Check size={18} className="text-success" />
          <span>{feature}</span>
        </li>
      ))}
    </ul>
    <button 
      className={`btn plan-btn ${current ? 'current-btn' : (highlighted ? 'btn-primary' : 'btn-secondary')}`}
      onClick={() => !current && onUpgrade(title)}
      disabled={current || loading}
    >
      {loading ? <Loader2 className="spin" size={18} /> : (current ? 'Current Plan' : cta)}
      {!current && !loading && <ArrowRight size={18} />}
    </button>
  </div>
);

const UsageBar = ({ label, current, total, colorClass }) => {
  const percentage = Math.min(100, (current / total) * 100);
  return (
    <div className="usage-item">
      <div className="usage-info">
        <span className="usage-label">{label}</span>
        <span className="usage-stats">{current} / {total}</span>
      </div>
      <div className="neon-progress-container">
        <div 
          className={`neon-progress-fill ${colorClass}`} 
          style={{ width: `${percentage}%` }}
        ></div>
      </div>
    </div>
  );
};

const Billing = () => {
  const [loadingPlan, setLoadingPlan] = useState(null);
  const [history] = useState([
    { id: 'INV-2024-001', date: 'Jul 01, 2024', amount: '$12.00', status: 'Paid' },
    { id: 'INV-2024-002', date: 'Jun 01, 2024', amount: '$12.00', status: 'Paid' },
    { id: 'INV-2024-003', date: 'May 01, 2024', amount: '$12.00', status: 'Paid' },
  ]);

  const handleCheckout = async (planTitle) => {
    setLoadingPlan(planTitle);
    try {
      // 1. Create subscription on the backend
      const subscriptionData = await api.post('/razorpay/create-subscription', {
        plan: planTitle.toLowerCase()
      });

      // 2. Configure Razorpay options
      const options = {
        key: import.meta.env.VITE_RAZORPAY_KEY_ID || 'rzp_test_placeholder', // Should be in env vars
        subscription_id: subscriptionData.subscription_id,
        name: 'Clutsch',
        description: `${planTitle} Subscription`,
        image: '/logo.png',
        handler: async function (response) {
                      // 3. Verify payment on the backend
                      try {
                        await api.post('/razorpay/verify-payment', {
                          razorpay_payment_id: response.razorpay_payment_id,
                          razorpay_subscription_id: response.razorpay_subscription_id,
                          razorpay_signature: response.razorpay_signature
                        });
                        showToast('Subscription successful! Your account has been upgraded.', 'success');
                        window.location.reload();
                      } catch (err) {
                        showToast('Payment verification failed. Please contact support.', 'error');
                      }
                    },
                    prefill: {
                      name: subscriptionData.user_name,
                      email: subscriptionData.user_email
                    },
                    theme: {
                      color: '#2563eb'
                    }
                  };

                  const rzp = new window.Razorpay(options);
                  rzp.on('payment.failed', function (response) {
                    showToast('Payment failed: ' + response.error.description, 'error');
                  });
                  rzp.open();
                } catch (err) {
                  showToast('Failed to initiate checkout. Please try again.', 'error');
                } finally {
                  setLoadingPlan(null);
                }
  };

  const plans = [
    {
      title: 'Free',
      price: '0',
      cta: 'Downgrade',
      features: [
        '2 Integrations',
        '50 Messages/mo',
        'AI Priority Scoring',
        'Basic Support'
      ]
    },
    {
      title: 'Pro',
      price: '12',
      cta: 'Get Pro',
      features: [
        'All Integrations',
        'Unlimited Messages',
        'AI Priority Scoring',
        'Quick Actions',
        'Advanced Search',
        'Mobile Access'
      ],
      current: true
    },
    {
      title: 'SME',
      price: 'Custom',
      isCustom: true,
      cta: 'Contact Sales',
      highlighted: true,
      features: [
        'Everything in Pro',
        'Up to 20 Users',
        'Team Shared Feeds',
        'Delegation Workflow',
        'Priority Support'
      ]
    },
    {
      title: 'Enterprise',
      price: 'Custom',
      isCustom: true,
      cta: 'Contact Sales',
      features: [
        'Everything in SME',
        'Unlimited Users',
        'Custom Integrations',
        'SAML / SSO',
        'Dedicated Manager',
        'Analytics'
      ]
    }
  ];

  return (
    <div className="billing-container animate-in">
      <header className="page-header">
        <h1>Billing & Subscription</h1>
        <p>Manage your plan, usage, and billing history.</p>
      </header>

      <section className="billing-grid">
        <div className="billing-main">
          <div className="section-title">
            <h2>Select a Plan</h2>
            <p>Scale Clutsch to your needs.</p>
          </div>
          <div className="plans-container">
            {plans.map((plan, i) => (
              <PlanCard 
                key={i} 
                {...plan} 
                onUpgrade={handleCheckout}
                loading={loadingPlan === plan.title}
              />
            ))}
          </div>

          <div className="card glass-effect usage-card">
            <div className="card-header">
              <h3>Usage Limits</h3>
              <div className="usage-reset">Resets in 12 days</div>
            </div>
            <div className="usage-grid">
              <UsageBar 
                label="Active Integrations" 
                current={4} 
                total={10} 
                colorClass="neon-blue" 
              />
              <UsageBar 
                label="Team Members" 
                current={8} 
                total={20} 
                colorClass="neon-purple" 
              />
              <UsageBar 
                label="AI Items Processed" 
                current={1250} 
                total={5000} 
                colorClass="neon-yellow" 
              />
              <UsageBar 
                label="Smart Responses" 
                current={45} 
                total={100} 
                colorClass="neon-green" 
              />
            </div>
          </div>
        </div>

        <aside className="billing-sidebar">
          <div className="card glass-effect payment-method">
            <h3>Payment Method</h3>
            <div className="card-details">
              <CreditCard size={24} />
              <div>
                <p className="card-number">•••• •••• •••• 4242</p>
                <p className="card-expiry">Expires 12/26</p>
              </div>
            </div>
            <button className="btn-text">Update Method</button>
          </div>

          <div className="card glass-effect billing-history">
            <h3>Billing History</h3>
            <div className="history-list">
              {history.map((item, i) => (
                <div key={i} className="history-item">
                  <div className="history-info">
                    <p className="history-id">{item.id}</p>
                    <p className="history-date">{item.date}</p>
                  </div>
                  <div className="history-actions">
                    <span className="history-amount">{item.amount}</span>
                    <button className="icon-btn" title="Download Invoice">
                      <Download size={16} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="enterprise-cta card glass-effect">
            <ShieldCheck size={48} className="text-purple" />
            <h3>Need more control?</h3>
            <p>Enterprise features include custom security protocols and SSO.</p>
            <button className="btn btn-primary">Contact Sales</button>
          </div>
        </aside>
      </section>
    </div>
  );
};


export default Billing;
