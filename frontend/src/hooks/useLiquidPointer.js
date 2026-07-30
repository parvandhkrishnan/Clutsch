import { useEffect, useRef } from 'react';

/**
 * Drives the specular hotspot on .btn-liquid by writing --px / --py.
 *
 * Deliberately vanilla. The whole job is "set two custom properties on
 * pointermove", and an animation library's value graph and spring solver would
 * be ~34 kB of dead weight for that.
 *
 * Three details that matter more than they look:
 *
 *  - No useState anywhere. State would re-render the React tree on every
 *    pointer event; these are direct DOM writes on a ref.
 *  - Writes are coalesced into one rAF. pointermove fires well above 60 Hz on
 *    high-poll-rate mice.
 *  - The rect is cached on pointerenter, never read inside the rAF. Reading
 *    getBoundingClientRect in the same frame you write styles forces a
 *    synchronous layout, which is measurable on a page as dense as Admin.
 *
 * Listeners attach to the node directly rather than through React props so
 * they can be passive and skip React's scheduler entirely.
 */
export function useLiquidPointer() {
  const ref = useRef(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const mqFine = matchMedia('(hover: hover) and (pointer: fine)');
    const mqMotion = matchMedia('(prefers-reduced-motion: reduce)');

    let rect = null;
    let rafId = 0;
    let clientX = 0;
    let clientY = 0;
    let attached = false;

    const commit = () => {
      rafId = 0;
      if (!rect) return;
      const x = ((clientX - rect.left) / rect.width) * 100;
      const y = ((clientY - rect.top) / rect.height) * 100;
      el.style.setProperty('--px', `${x.toFixed(2)}%`);
      el.style.setProperty('--py', `${y.toFixed(2)}%`);
    };

    const onMove = (e) => {
      clientX = e.clientX;
      clientY = e.clientY;
      if (!rafId) rafId = requestAnimationFrame(commit);
    };
    const onEnter = () => {
      rect = el.getBoundingClientRect();
      el.style.setProperty('--pa', '1');
    };
    const onLeave = () => {
      // Fade the highlight out via --pa rather than clearing --px/--py, which
      // would snap it back to centre mid-fade.
      el.style.setProperty('--pa', '0');
      if (rafId) { cancelAnimationFrame(rafId); rafId = 0; }
      rect = null;
    };
    const invalidate = () => { if (rect) rect = el.getBoundingClientRect(); };

    const attach = () => {
      if (attached || !mqFine.matches || mqMotion.matches) return;
      el.addEventListener('pointerenter', onEnter, { passive: true });
      el.addEventListener('pointermove', onMove, { passive: true });
      el.addEventListener('pointerleave', onLeave, { passive: true });
      window.addEventListener('resize', invalidate, { passive: true });
      window.addEventListener('scroll', invalidate, { passive: true, capture: true });
      attached = true;
    };
    const detach = () => {
      if (!attached) return;
      el.removeEventListener('pointerenter', onEnter);
      el.removeEventListener('pointermove', onMove);
      el.removeEventListener('pointerleave', onLeave);
      window.removeEventListener('resize', invalidate);
      window.removeEventListener('scroll', invalidate, { capture: true });
      if (rafId) { cancelAnimationFrame(rafId); rafId = 0; }
      el.style.removeProperty('--pa');
      attached = false;
    };

    // Touch devices are excluded on purpose, not by omission: pointermove
    // fires throughout a touch-drag, so attaching there would run this on
    // every scroll gesture. They get a static press-bloom in CSS instead.
    const sync = () => {
      if (mqFine.matches && !mqMotion.matches) attach();
      else detach();
    };

    sync();
    mqFine.addEventListener('change', sync);
    mqMotion.addEventListener('change', sync);

    return () => {
      mqFine.removeEventListener('change', sync);
      mqMotion.removeEventListener('change', sync);
      detach();
    };
  }, []);

  return ref;
}

export default useLiquidPointer;
