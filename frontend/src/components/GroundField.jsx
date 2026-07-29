/**
 * The luminous field every glass surface refracts.
 *
 * Mounted exactly once, at the App root, outside the Router — it must not
 * unmount on navigation, and it must be a direct descendant of <body> with no
 * transformed/filtered/contained ancestor between it and the glass surfaces
 * that sample it (see the note in styles/material.css).
 *
 * Purely decorative, so it is hidden from assistive tech.
 */
const GroundField = () => <div className="ground" aria-hidden="true" />;

export default GroundField;
