import { Mail, MessageSquare } from 'lucide-react';

/**
 * Renders the real brand mark for a communication source.
 *
 * Replaces the previous approach of mapping every service to a generic lucide
 * glyph, which collapsed distinct brands onto the same icon — Gmail and
 * Outlook were both `Mail`, Slack and WhatsApp were both `MessageCircle` — so
 * the icon carried no information at all.
 *
 * Unknown sources fall back to a neutral glyph rather than borrowing another
 * brand's mark, which would be actively misleading.
 */

const BRAND_LOGOS = {
  gmail: 'gmail',
  outlook: 'outlook',
  slack: 'slack',
  teams: 'teams',
  msteams: 'teams',
  microsoftteams: 'teams',
  whatsapp: 'whatsapp',
  jira: 'jira',
  linear: 'linear',
};

const SourceLogo = ({ source, size = 20, className = '' }) => {
  const key = String(source || '').toLowerCase().replace(/[\s._-]/g, '');
  const slug = BRAND_LOGOS[key];

  if (slug) {
    return (
      <img
        src={`/logos/${slug}.svg`}
        // Decorative: every current call site renders the source name in
        // adjacent text, so announcing it again would just be noise.
        alt=""
        width={size}
        height={size}
        className={`source-logo ${className}`.trim()}
        loading="lazy"
        decoding="async"
      />
    );
  }

  const Fallback = key === 'email' ? Mail : MessageSquare;
  return <Fallback size={size} className={className} aria-hidden="true" />;
};

export default SourceLogo;
