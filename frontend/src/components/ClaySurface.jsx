import React from 'react';

/**
 * ClaySurface — Pressed-clay structural material.
 * Use for: cards, panels, input fields, sidebars, modals.
 *
 * Variants:
 *   - "card"   (default) raised clay surface
 *   - "input"  inset/pressed clay for form fields
 *   - "sidebar" tall vertical clay panel
 *   - "modal"  clay card on a glass overlay
 */
export default function ClaySurface({ variant = 'card', children, className = '', ...props }) {
  const variantClasses = {
    card: 'clay',
    input: 'clay-input',
    sidebar: 'clay sidebar',
    modal: 'clay modal-card',
    panel: 'clay focus-panel',
  };

  const cls = `${variantClasses[variant] || variantClasses.card} ${className}`.trim();

  if (variant === 'input') {
    return (
      <input className={cls} {...props} />
    );
  }

  return (
    <div className={cls} {...props}>
      {children}
    </div>
  );
}

export function ClayCard({ children, className = '', ...props }) {
  return (
    <div className={`clay ${className}`} {...props}>
      {children}
    </div>
  );
}

export function ClayInput({ className = '', ...props }) {
  return (
    <input className={`clay-input ${className}`} {...props} />
  );
}