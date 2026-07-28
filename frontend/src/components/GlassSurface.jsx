/**
 * GlassSurface — Apple-style liquid glass material.
 * Use for: primary buttons, nav/tab bar, floating controls, modal CTAs.
 *
 * Variants:
 *   - "button"    (default) pill-shaped interactive button
 *   - "primary"   accent-colored primary action button
 *   - "nav"       navigation/tab item
 *   - "panel"     floating glass panel (toast, bulk action bar)
 *   - "chip"      small filter/tier chip
 */
export default function GlassSurface({ variant = 'button', children, className = '', active, onClick, disabled, ...props }) {
  const baseClass = 'glass';

  const variantClasses = {
    button: 'glass-button',
    primary: 'glass-button primary',
    nav: 'glass-button nav-item',
    panel: 'glass',
    chip: 'glass-button tier-chip',
  };

  const cls = `${baseClass} ${variantClasses[variant] || variantClasses.button} ${active ? 'active' : ''} ${className}`.trim();

  return (
    <button className={cls} onClick={onClick} disabled={disabled} {...props}>
      {children}
    </button>
  );
}

export function GlassPanel({ children, className = '', ...props }) {
  return (
    <div className={`glass ${className}`} {...props}>
      {children}
    </div>
  );
}