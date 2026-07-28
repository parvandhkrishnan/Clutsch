import React, { useState, useEffect, useCallback } from 'react';
import {
  Check,
  CreditCard,
  ShieldCheck,
  ArrowRight,
  Loader2,
  Receipt
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
  const safeTotal = total > 0 ? total : 1;
  const percentage = Math.min(100, (current / safeTotal) * 100);
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

const PLAN_FEATURES = {
  Free: [
    '2 Integrations',
    '50 Messages/mo',
    'AI Priority Scoring',
    'Basic Support'
  ],
  Pro: [
    'All Integrations',
    'Unlimited Messages',
    'AI Priority Scoring',
    'Quick Actions',
    'Advanced Search',
    'Mobile Access'
  ],
  SME: [
    'Everything in Pro',
    'Up to 20 Users',
    'Team Shared Feeds',
    'Delegation Workflow',
    'Priority Support'
  ],
  Enterprise: [
    'Everything in SME',
    'Unlimited Users',
    'Custom Integrations',
    'SAML / SSO',
    'Dedicated Manager',
    'Analytics'
  ]
};

const Billing = () => {
  const [loadingPlan, setLoadingPlan] = useState(null);
  const [billing, setBilling] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchBilling = useCallback(async () => {
    try {
      const data = await api.get('/razorpay/status');
      setBilling(data);
      setError(null);
    } catch (err) {
      console.error("Failed to fetch billing info:", err);
      setError(err.message || "Failed to load billing information.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchBilling();
  }, [fetchBilling]);

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

  const currentPlanName = billing?.plan || null;

  const plans = [
    {
      title: 'Free',
      price: '0',
      cta: 'Downgrade',
      features: PLAN_FEATURES.Free
    },
    {
      title: 'Pro',
      price: '12',
      cta: 'Get Pro',
      features: PLAN_FEATURES.Pro
    },
    {
      title: 'SME',
      price: 'Custom',
      isCustom: true,
      cta: 'Contact Sales',
      highlighted: true,
      features: PLAN_FEATURES.SME
    },
    {
      title: 'Enterprise',
      price: 'Custom',
      isCustom: true,
      cta: 'Contact Sales',
      features: PLAN_FEATURES.Enterprise
    }
  ];

  const usage = billing?.usage || { active_integrations: 0, team_members: 0, ai_items_processed: 0, smart_responses: 0 };
  const limits = billing?.limits || { active_integrations: 0, team_members: 0, ai_items_processed: 0, smart_responses: 0 };

  if (loading) {
    return (
      <div className="billing-container animate-in">
        <header className="page-header">
          <h1>Billing & Subscription</h1>
          <p>Manage your plan, usage, and billing history.</p>
        </header>
        <div className="loading-state" style={{ textAlign: 'center', padding: '60px 20px' }} role="status">
          <Loader2 size={48} className="spin" style={{ marginBottom: '16px' }} />
          <p>Loading billing information...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="billing-container animate-in">
      <header className="page-header">
        <h1>Billing & Subscription</h1>
        <p>Manage your plan, usage, and billing history.</p>
      </header>

      {error && <div className="error-state">{error}</div>}

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
                current={currentPlanName === plan.title}
                onUpgrade={handleCheckout}
                loading={loadingPlan === plan.title}
              />
            ))}
          </div>

          <div className="card glass-effect usage-card">
            <div className="card-header">
              <h3>Usage Limits</h3>
            </div>
            <div className="usage-grid">
              <UsageBar
                label="Active Integrations"
                current={usage.active_integrations}
                total={limits.active_integrations}
                colorClass="neon-blue"
              />
              <UsageBar
                label="Team Members"
                current={usage.team_members}
                total={limits.team_members}
                colorClass="neon-purple"
              />
              <UsageBar
                label="AI Items Processed"
                current={usage.ai_items_processed}
                total={limits.ai_items_processed}
                colorClass="neon-yellow"
              />
              <UsageBar
                label="Smart Responses"
                current={usage.smart_responses}
                total={limits.smart_responses}
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
                <p className="card-number">No payment method on file</p>
              </div>
            </div>
            <button className="btn-text" disabled title="Payment method management isn't available yet.">
              Update Method
            </button>
          </div>

          <div className="card glass-effect billing-history">
            <h3>Billing History</h3>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', padding: '32px 16px', gap: '12px', color: 'var(--text-muted)' }}>
              <Receipt size={32} />
              <p style={{ margin: 0 }}>
                Invoice history isn't available yet — there is no invoice-list endpoint on the
                backend today. Past invoices will appear here once that's implemented.
              </p>
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
