import { useRef, useEffect, useCallback } from 'react';

/**
 * Focus trap hook for modals. Traps Tab/Shift+Tab within the container.
 * @param {boolean} active - Whether the trap is active (usually isOpen)
 * @returns {{ ref: React.RefObject, onKeyDown: Function }}
 */
export default function useFocusTrap(active = true) {
  const containerRef = useRef(null);

  const handleKeyDown = useCallback((e) => {
    if (e.key !== 'Tab' || !containerRef.current) return;
    
    const focusable = containerRef.current.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    if (focusable.length === 0) return;

    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    if (e.shiftKey) {
      if (document.activeElement === first) {
        e.preventDefault();
        last.focus();
      }
    } else {
      if (document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  }, []);

  useEffect(() => {
    if (!active || !containerRef.current) return;
    // Focus the first focusable element when modal opens
    const focusable = containerRef.current.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    if (focusable.length > 0) {
      setTimeout(() => focusable[0].focus(), 50);
    }
  }, [active]);

  return { ref: containerRef, onKeyDown: handleKeyDown };
}