import { useEffect, useRef, useCallback } from 'react';

/**
 * useFocusTrap
 * Accessibility helper for modal dialogs.
 *
 * - Traps Tab / Shift+Tab focus within the referenced container so keyboard
 *   users cannot tab out of an open modal (wraps focus first <-> last).
 * - Moves focus into the modal on open and restores focus to the previously
 *   focused element on close/unmount.
 * - Calls onClose (if provided) when Escape is pressed.
 *
 * Usage:
 *   const { containerRef, onKeyDown } = useFocusTrap(onClose);
 *   <div className="modal-overlay" ...>
 *     <div className="modal-content" ref={containerRef} onKeyDown={onKeyDown}
 *          role="dialog" aria-modal="true">
 *       ...
 *
 * @param {Function} [onClose] optional handler invoked on Escape.
 * @param {boolean} [active=true] when the modal is open. When false the trap
 *   is inactive (used by modals that stay mounted and toggle via an isOpen prop).
 * @returns {{ containerRef: React.RefObject, onKeyDown: Function }}
 */
export default function useFocusTrap(onClose, active = true) {
  const containerRef = useRef(null);
  const previouslyFocused = useRef(null);

  const getFocusable = useCallback(() => {
    if (!containerRef.current) return [];
    return Array.from(
      containerRef.current.querySelectorAll(
        'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
    ).filter((el) => el.offsetParent !== null || el === document.activeElement);
  }, []);

  useEffect(() => {
    if (!active) return undefined;
    previouslyFocused.current = document.activeElement;
    // Move focus into the modal (first focusable, else the container itself).
    const focusables = getFocusable();
    if (focusables.length > 0) {
      focusables[0].focus();
    } else if (containerRef.current) {
      containerRef.current.focus();
    }
    const restore = previouslyFocused.current;
    return () => {
      // Restore focus to whatever was focused before the modal opened.
      if (restore && typeof restore.focus === 'function') {
        restore.focus();
      }
    };
  }, [getFocusable, active]);

  const onKeyDown = useCallback(
    (e) => {
      if (e.key === 'Escape' && typeof onClose === 'function') {
        e.stopPropagation();
        onClose();
        return;
      }
      if (e.key !== 'Tab') return;

      const focusables = getFocusable();
      if (focusables.length === 0) {
        e.preventDefault();
        return;
      }
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      const active = document.activeElement;

      if (e.shiftKey) {
        if (active === first || !containerRef.current.contains(active)) {
          e.preventDefault();
          last.focus();
        }
      } else if (active === last) {
        e.preventDefault();
        first.focus();
      }
    },
    [getFocusable, onClose]
  );

  return { containerRef, onKeyDown };
}
