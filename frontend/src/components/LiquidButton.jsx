import { useLiquidPointer } from '../hooks/useLiquidPointer';

/**
 * Large primary CTA rendered in liquid glass, with a specular highlight that
 * tracks the pointer.
 *
 * Reserved for large buttons on purpose. The highlight is a radial gradient
 * that repaints as the pointer moves — trivial for a 200x48 control, wasteful
 * on a chip or a table row. `.btn-liquid`'s 44px min-height enforces the same
 * rule from the CSS side.
 *
 * `brand` tints the under-fill; without it the glass is neutral and does not
 * read as the primary action on a colourless dark field.
 */
const LiquidButton = ({
  brand = true,
  className = '',
  type = 'button',
  children,
  ...props
}) => {
  const ref = useLiquidPointer();
  const cls = `btn-liquid ${brand ? 'btn-liquid--brand' : ''} ${className}`
    .replace(/\s+/g, ' ')
    .trim();

  return (
    <button ref={ref} type={type} className={cls} {...props}>
      {children}
    </button>
  );
};

export default LiquidButton;
