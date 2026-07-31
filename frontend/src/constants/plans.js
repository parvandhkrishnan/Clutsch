/**
 * Plan tiers — single source of truth for the landing page's pricing grid and
 * the Billing page's plan selector.
 *
 * Tier names must match backend/razorpay_routes.py's VALID_PLANS
 * ("Free", "Pro", "SME", "Enterprise"), since those strings are sent to
 * /razorpay/create-subscription and used as the billing plan key.
 *
 * Only the CTA label differs between the two surfaces (marketing says
 * "Get Started Free", account management says "Downgrade"), so that stays at
 * the call site. Everything else lives here.
 *
 * ⚠ KNOWN COPY/BACKEND MISMATCH — not changed here, because it is a pricing
 * decision rather than a UI bug. Pro advertises "Unlimited Messages", but
 * backend/database.py's PLAN_LIMITS caps Pro at ai_items_processed: 5000, and
 * the Billing page renders that limit in its usage meter. A Pro user therefore
 * sees "Unlimited Messages" on the plan card and "X / 5000" in their own usage
 * bar on the same screen. Resolve by either raising the backend limit or
 * softening the copy.
 */

export const PLANS = [
  {
    id: 'Free',
    name: 'Free',
    price: '0',
    isFree: true,
    features: [
      '2 Integrations',
      '50 Messages/mo',
      'AI Priority Scoring',
      'Basic Support',
    ],
  },
  {
    id: 'Pro',
    name: 'Pro',
    price: '12',
    features: [
      'All Integrations',
      'Unlimited Messages',
      'AI Priority Scoring',
      'Quick Actions',
      'Advanced Search',
      'Mobile Access',
    ],
  },
  {
    id: 'SME',
    name: 'SME',
    price: 'Custom',
    isCustom: true,
    features: [
      'Everything in Pro',
      'Up to 20 Users',
      'Team Shared Feeds',
      'Delegation Workflow',
      'Priority Support',
    ],
  },
  {
    id: 'Enterprise',
    name: 'Enterprise',
    price: 'Custom',
    isCustom: true,
    features: [
      'Everything in SME',
      'Unlimited Users',
      'Custom Integrations',
      'SAML / SSO',
      'Dedicated Manager',
      'Analytics',
    ],
  },
];

/**
 * Only Pro is self-serve; SME and Enterprise route to sales. Mirrors
 * backend/razorpay_routes.py's SELF_SERVE_PAID_PLANS.
 */
export const SELF_SERVE_PAID_PLANS = ['Pro'];

export const planCta = (plan, { context }) => {
  if (plan.isCustom) return 'Contact Sales';
  if (plan.isFree) return context === 'billing' ? 'Downgrade' : 'Get Started Free';
  return `Get ${plan.name}`;
};
