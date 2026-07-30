import { Moon, Sun } from 'lucide-react';
import { usePreferences } from '../context/PreferencesContext';

/**
 * Theme switch.
 *
 * Lives in a component rather than inline in the sidebar because the sidebar
 * only renders on authenticated routes — the landing page and the login screen
 * had no way to reach it, which is exactly where a first-time visitor forms
 * their impression of the theme.
 *
 * `variant="rail"`  full-width row, matches .sidebar-item
 * `variant="pill"`  compact icon-and-label button for public page chrome
 * `variant="icon"`  icon only, for tight corners
 */
const ThemeToggle = ({ variant = 'rail', className = '' }) => {
  const { theme, toggleTheme } = usePreferences();
  const isDark = theme === 'dark';
  const label = isDark ? 'Light theme' : 'Dark theme';

  const base = variant === 'rail' ? 'sidebar-item' : 'theme-toggle';
  const cls = `${base} theme-toggle--${variant} ${className}`.trim();

  return (
    <button
      type="button"
      className={cls}
      onClick={toggleTheme}
      aria-pressed={isDark}
      // Icon-only variant has no visible text, so it needs its own name.
      aria-label={`Switch to ${isDark ? 'light' : 'dark'} theme`}
      title={label}
    >
      {isDark ? <Sun size={18} /> : <Moon size={18} />}
      {variant !== 'icon' && <span>{label}</span>}
    </button>
  );
};

export default ThemeToggle;
