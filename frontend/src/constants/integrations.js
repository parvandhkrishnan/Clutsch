/**
 * The integrations the product actually supports — single source of truth.
 *
 * Mirrors the ADAPTERS map in backend/integration_routes.py. Keep them in
 * sync: if an adapter is added or removed there, change this list, and the
 * marketing strip, the Integrations page, the onboarding tiles and the
 * connect modals all follow automatically.
 *
 * This exists because the list was previously hardcoded in two places and
 * drifted: the landing page advertised Linear, which has no backend adapter
 * and could never be connected. Anyone reaching the app from that page would
 * have found six integrations where seven were promised.
 */

export const INTEGRATIONS = [
  {
    id: 'gmail',
    name: 'Gmail',
    description: 'Connect your personal or work Gmail account to prioritize emails.',
    account: 'john.doe@gmail.com',
  },
  {
    id: 'outlook',
    name: 'Outlook',
    description: 'Sync your Microsoft Outlook inbox for unified communication.',
    account: 'work@company.com',
  },
  {
    id: 'slack',
    name: 'Slack',
    description: 'Identify urgent messages and threads across all your Slack channels.',
    account: 'Team Slack',
  },
  {
    id: 'teams',
    name: 'MS Teams',
    description: 'Collaborate and prioritize messages from Microsoft Teams.',
    account: 'Work Teams',
  },
  {
    id: 'whatsapp',
    name: 'WhatsApp',
    description: 'Stay on top of your WhatsApp chats with AI-driven priority.',
    account: '+123456789',
  },
  {
    id: 'jira',
    name: 'Jira',
    description: 'Track project updates and ticket priorities from Jira.',
    account: 'John Doe',
  },
];

/** Keyed by id, for the O(1) lookups the Integrations page needs. */
export const INTEGRATION_METADATA = Object.fromEntries(
  INTEGRATIONS.map(({ id, ...rest }) => [id, rest])
);

export const INTEGRATION_IDS = INTEGRATIONS.map((i) => i.id);
