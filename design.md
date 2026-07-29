# Design — Clutsch

Locked design system. Future work reads this file first; every page defers
to it. Amend intentionally — this file is the rule, not per-page taste.

Seeded from `design/redesign-v2/DESIGN_SYSTEM.md` (Fillout-inspired v2 spec),
with one deliberate deviation: the accent color is dropped in favor of a
fully monochrome system, per explicit product direction. Cross-checked
against `taste-skill` (anti-slop / font+color discipline) and `ui-ux-pro-max`
(accessibility, touch-target, forms guideline categories) — see § Notes.

## System
- Genre · **modern-minimal** (Stripe / Linear / ElevenLabs school — confirmed
  fit: SaaS, dashboard, billing, B2B all named in the brief; a monochrome
  accent — here a dedicated dark gray, one step lighter than body-text ink —
  is explicitly canonical for this genre, not a workaround)
- Macrostructure, by page family:
  - **App shell** (Dashboard, Admin, Settings, Tasks, Analytics, Billing,
    Integrations, HelpCenter) · **Bento Grid** — matches the existing
    `03-dashboard.png` mockup's irregular-block layout and the priority-orb
    component already spec'd in the source doc. Nav: persistent side-rail
    (the existing `Sidebar.jsx`, restyled — not one of Hallmark's marketing
    nav archetypes, this is app-shell chrome). No footer in the app shell.
  - **Marketing / pre-auth** (LandingPage, Login, Onboarding, SSOPopup) ·
    **Marquee Hero**, two-column (title-left / lede-right per modern-minimal
    voice) — replaces the current stacked wordmark-nav + 3-col-feature-grid +
    4-tower-pricing + 4-column-footer template flagged in the Phase 1 audit.
    Nav: N5 Floating pill. Footer: Ft2 Inline single line.
- Theme · **custom** (tuned, not catalog — the brief names concrete brand
  neutrals from the source spec, which the 20-theme catalog can't carry
  verbatim): vibe *"calm, warm off-white, monochrome ink, one quiet signal
  color reserved for priority only"*
- Axes · light paper-band / geometric-sans display / **neutral accent-hue**
  (zero chroma sitewide — see § Priority color below for the one exception)

## Tokens (canonical · `tokens.css` is the source of truth)
```css
:root {
  /* Neutrals — converted from design/redesign-v2/DESIGN_SYSTEM.md hex via
     sRGB→OKLab, not eyeballed. Warm-tinted (H≈80-90), never pure black/white. */
  --color-paper:      oklch(98.5% 0.0013 106);  /* was #FAFAF9 canvas */
  --color-paper-2:    oklch(100%   0      0);    /* was #FFFFFF card surface */
  --color-paper-3:    oklch(96.7% 0.0029 85);   /* was #F5F4F2 hover/inset */
  --color-rule:       oklch(93.1% 0.0058 85);   /* was #EAE8E4 default border */
  --color-rule-strong: oklch(88.7% 0.0093 78);  /* was #DDD9D3 input border */
  --color-ink:         oklch(22.3% 0.0025 68);  /* was #1C1B1A — warm near-black, never pure #000 */
  --color-ink-2:        oklch(51.8% 0.0100 85);  /* was #6B6862 body/secondary text */
  --color-ink-3:        oklch(68.0% 0.0138 87);  /* was #9C988F meta/placeholder text */

  /* Accent — monochrome dark gray, same warm neutral family as ink/paper
     (never a colder, unrelated gray — one gray family, per taste-skill).
     Deliberately distinct from --color-ink so interactive elements (buttons,
     links, focus rings) read as a separate affordance from body text, not
     just "the same near-black used for everything." */
  --color-accent:      oklch(39.9% 0.0077 75);   /* warm dark gray, was #4A4743 */
  --color-accent-hover: oklch(32% 0.0077 75);    /* one step darker on hover/press */
  --color-accent-ink:  var(--color-paper-2);      /* text/icon color ON the accent fill */
  --color-accent-soft: var(--color-paper-3);      /* selected-row / soft-badge background */
  --color-focus:       var(--color-accent);

  --font-display: "Satoshi", "Inter", -apple-system, "Segoe UI", sans-serif;
  --font-body:    "Inter", -apple-system, "Segoe UI", sans-serif;
  --font-mono:    "JetBrains Mono", ui-monospace, monospace;

  /* 4pt spacing scale, 9 named steps (Hallmark standard — replaces raw px) */
  --space-3xs: 0.125rem;  --space-2xs: 0.25rem;  --space-xs: 0.5rem;
  --space-sm:  0.75rem;   --space-md:  1rem;     --space-lg: 1.5rem;
  --space-xl:  2.5rem;    --space-2xl: 4rem;     --space-3xl: 6rem;

  /* Type scale, 1.25 ratio */
  --text-xs: 0.75rem; --text-sm: 0.875rem; --text-md: 1rem; --text-lg: 1.125rem;
  --text-xl: 1.5rem; --text-2xl: 2rem; --text-display-s: 2.75rem; --text-display: 3.75rem;

  --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
  --dur-fast: 150ms; --dur-base: 200ms; --dur-slow: 250ms;

  --radius-input: 8px; --radius-card: 12px; --radius-panel: 16px; --radius-pill: 999px;

  /* Z-index — six named levels, replaces the three ad-hoc 9999s found in audit */
  --z-base: 1; --z-raised: 10; --z-dropdown: 100;
  --z-sticky: 200; --z-modal: 400; --z-toast: 500;
}
```

### Priority color — the one sanctioned exception to monochrome
Priority (urgent/high/medium/low) is the single semantic signal in the
product and stays color-coded, reserved exclusively for the priority orb,
score chip, and tier badge — nowhere else. One canonical set (replaces the
three conflicting palettes found in the audit — Dashboard's gauge, Analytics'
charts, and the dead v1 stylesheet each disagreed):
```css
:root {
  --priority-urgent: oklch(62.6% 0.201 21);   /* was #E8434F */
  --priority-high:   oklch(75.0% 0.167 51);   /* was #FF8A3D */
  --priority-medium: oklch(81.7% 0.160 83);   /* was #F5B826 */
  --priority-low:    oklch(71.3% 0.101 172);  /* was #56B79B */
}
```

## CTA voice
- Primary · `var(--color-accent)` fill (dark gray, not pure black), `var(--color-accent-ink)`
  text, `--radius-pill` on marketing pages / `--radius-input` in-app, 44px
  tall on marketing (touch-target minimum), 40px in dense app UI. Hover:
  `var(--color-accent-hover)` + 1px lift.
- Secondary · `var(--color-paper-2)` fill, `1px solid var(--color-rule-strong)`,
  `var(--color-ink)` text, same radius as primary. Hover → `var(--color-paper-3)`.
- Ghost · transparent, `var(--color-ink-2)` text. Hover → `var(--color-paper-3)`.
- No two CTAs with the same intent on one page (e.g. "Get started" +
  "Sign up free" both present) — pick one label per intent, reuse it.

## Motion stance
- Minimal — reveals are off by default; the page is composed, not animated in.
- 1 orchestrated entrance on first load maximum; everything else is just there.
- Interactive elements: `transform`/`opacity` only, `--ease-out`, never
  bounce/overshoot. `:focus-visible` ring appears instantly, never transitions.
- Reduced-motion fallback · ≤150ms opacity crossfade, respects
  `prefers-reduced-motion`.

## Notes
- **Font pairing (Satoshi + Inter) is kept from the source spec** — cross-
  checked against taste-skill's approved-pairing list (Satoshi pairs
  canonically with a mono for data/code) and its "Inter is acceptable for an
  explicitly neutral / Linear-style feel" exception, which this genre is.
  The audit found Satoshi loaded via `@import` but never actually referenced
  in CSS — Phase 3 must wire `--font-display: Satoshi` into real headings,
  not just fix the token name.
- **Accessibility bar, made explicit because the audit found it nearly
  absent:** every interactive element ships a real `:focus-visible` ring
  (not just the one toggle switch that currently has it), minimum touch
  target 44×44px with 8px+ spacing between adjacent targets (ui-ux-pro-max:
  Touch & Interaction, priority 2), icon-only buttons get `aria-label` not
  just `title`, and all four numeric-display surfaces (priority scores,
  percentages, dates, prices) get `font-variant-numeric: tabular-nums`.
- **One radius scale, applied consistently** (taste-skill's "shape
  consistency lock"): inputs 8px, cards 12px, panels/modals 16px, pills full
  — no page invents its own radius.
- **Real screenshots only.** The landing page's hand-drawn SVG dashboard
  mockup (flagged in the audit) is replaced with an actual product
  screenshot wrapped in a hairline-bordered `<figure>` per Phase 4, not
  redrawn chrome.
- **Inline `style={{}}` is retired as a pattern**, not just reduced — every
  page currently has 15-56 occurrences; Phase 3/4 extract them into the
  classes/tokens above so future theming isn't blocked by hardcoded values.

## Exports
`tokens.css` (in this project) is the source of truth once Phase 3 lands.
Additional export formats (Tailwind `@theme`, DTCG `tokens.json`, shadcn/ui
variables) can be added later on request — not needed now, the project ships
plain CSS custom properties.
