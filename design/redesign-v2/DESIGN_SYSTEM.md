# Clutsch — Design System v2 (Fillout-Inspired)

**Status:** High-fidelity design direction for the front-end redesign.
**Owner:** Product Designer · **Consumer:** Frontend Engineer
**Inspiration:** Fillout.com (primary), Linear, Notion, Raycast, Superhuman.

---

## 1. Design Philosophy

The v1 identity leaned dark, dense, and "power-user." v2 flips this to a **clean, light, approachable** aesthetic that reduces cognitive load — appropriate for a product whose entire promise is *making prioritization feel effortless*.

**Principles**
1. **Whitespace is a feature.** Generous padding and breathing room signal calm and control. Fight the urge to fill every pixel.
2. **Soft, not flat.** Subtle shadows and 1px borders give cards gentle lift without heavy skeuomorphism or neon glow.
3. **One confident accent.** The electric violet stays, but as an *accent on light* — not a dark-mode dominant. Color earns attention; most of the UI is neutral.
4. **Content-first hierarchy.** Large, friendly display type for headlines; quiet, readable body. Priority is communicated through position, weight, and a single orb — never a rainbow.
5. **Motion that reassures.** Transitions are smooth and short (150–250ms), easing on hover and state change. Nothing bounces or distracts.

---

## 2. Color System

### Neutrals (base)
| Token | Hex | Use |
|---|---|---|
| `--bg-canvas` | `#FAFAF9` | App background (warm off-white, not cold #FFF) |
| `--bg-surface` | `#FFFFFF` | Cards, panels, modals |
| `--bg-subtle` | `#F5F4F2` | Hover fills, inset wells, secondary surfaces |
| `--border` | `#EAE8E4` | Default 1px card/divider border |
| `--border-strong` | `#DDD9D3` | Inputs, emphasized dividers |
| `--text-primary` | `#1C1B1A` | Headlines, primary text (warm near-black) |
| `--text-secondary`| `#6B6862` | Body, labels |
| `--text-tertiary` | `#9C988F` | Meta, timestamps, placeholders |

### Accent (brand)
| Token | Hex | Use |
|---|---|---|
| `--accent` | `#6C3BFF` | Primary buttons, active states, links, focus ring |
| `--accent-hover` | `#5A2EE0` | Hover on primary actions |
| `--accent-soft` | `#F0EBFF` | Accent-tinted backgrounds, selected rows, badges |
| `--accent-border`| `#DCCFFF` | Borders on accent-soft surfaces |

### Priority scale (semantic — orbs & scores only)
Single-hue-per-band, muted and gradient-filled (no hard neon). Used **only** for the priority orb and score chip.
| Band | Score | Orb gradient | Chip text |
|---|---|---|---|
| Critical | 90–100 | `#FF6B6B → #E8434F` | `#C4303B` |
| High | 70–89 | `#FFB37A → #FF8A3D` | `#C96A1F` |
| Medium | 50–69 | `#FFD666 → #F5B826` | `#9A7A12` |
| Low | <50 | `#8FD8C4 → #56B79B` | `#2F8A72` |

> Rationale: priority is the ONE place color carries meaning. Keeping the rest of the UI neutral makes these orbs pop without shouting.

### Feedback
| Token | Hex |
|---|---|
| `--success` | `#2F8A72` |
| `--warning` | `#C96A1F` |
| `--danger` | `#E8434F` |
| `--info` | `#6C3BFF` |

---

## 3. Typography

**Family:** `Satoshi` for display/headings (or Inter as fallback), `Inter` for body/UI. System fallback: `-apple-system, "Segoe UI", sans-serif`.

| Role | Size / Line | Weight | Tracking |
|---|---|---|---|
| Display XL (hero) | 60 / 64 | 700 | −0.02em |
| Display L | 44 / 50 | 700 | −0.02em |
| Heading 1 | 32 / 40 | 600 | −0.01em |
| Heading 2 | 24 / 32 | 600 | −0.01em |
| Heading 3 | 18 / 26 | 600 | 0 |
| Body L | 17 / 28 | 400 | 0 |
| Body | 15 / 24 | 400 | 0 |
| Label | 13 / 18 | 500 | 0 |
| Caption / meta | 12 / 16 | 500 | 0.01em |

**Rules:** Headlines in `--text-primary`, tight leading. Body in `--text-secondary` for long reads. Never use pure black (#000) — always the warm `#1C1B1A`.

---

## 4. Spacing & Layout

- **Base unit:** 4px. Scale: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80.
- **Content max-width:** 1200px (marketing), 1440px (app shell).
- **Card padding:** 24px default, 20px compact, 32px feature.
- **Grid gutter:** 20–24px between bento cards.
- **Radii:** `--r-sm 8px` (chips, inputs) · `--r-md 12px` (buttons, small cards) · `--r-lg 16px` (cards) · `--r-xl 24px` (feature/hero panels) · `--r-full 999px` (orbs, pills, avatars).

### Bento grid
12-column responsive grid. Cards span varying widths/heights but always align to the grid and keep **≥20px gutters**. More breathing room than v1 — no more than ~65% of viewport covered by cards; the warm canvas shows through.

---

## 5. Elevation (shadows)

Soft, low-spread, cool-neutral — never harsh black.
| Token | Value | Use |
|---|---|---|
| `--shadow-xs` | `0 1px 2px rgba(28,27,26,.04)` | Inputs, chips |
| `--shadow-sm` | `0 1px 3px rgba(28,27,26,.06), 0 1px 2px rgba(28,27,26,.04)` | Cards at rest |
| `--shadow-md` | `0 4px 12px rgba(28,27,26,.08)` | Card hover, dropdowns |
| `--shadow-lg` | `0 12px 32px rgba(28,27,26,.10)` | Modals, popovers |
| `--shadow-accent` | `0 8px 24px rgba(108,59,255,.18)` | Primary CTA hover, orb ambient |

---

## 6. Components

### Buttons
- **Primary:** `--accent` fill, white text, `--r-md`, 40px tall (44px on marketing), weight 500. Hover → `--accent-hover` + `--shadow-accent` + 1px lift.
- **Secondary:** `--bg-surface` fill, `--border-strong` 1px, `--text-primary`. Hover → `--bg-subtle`.
- **Ghost:** transparent, `--text-secondary`. Hover → `--bg-subtle`.
- **Sizes:** sm 32px, md 40px, lg 44px. Icon buttons square with matching radius.

### Cards
`--bg-surface`, `--r-lg`, 1px `--border`, `--shadow-sm`. Hover (interactive cards): `--shadow-md` + border → `--accent-border` + 1px lift. 200ms ease.

### Inputs
44px tall, `--r-md`, `--bg-surface`, 1px `--border-strong`. Focus: 2px `--accent` ring (`0 0 0 3px --accent-soft`) + border `--accent`. Placeholder `--text-tertiary`.

### Priority orb
Circular gauge, `--r-full`, filled with the band gradient. Score number centered, weight 600, white text. A soft ambient shadow in the band color (low opacity) gives the "glow" — subtle, not neon. Sizes: 28px (list), 48px (card), 64px (detail). Optional thin progress ring around the orb showing score/100.

### Priority chip
Pill (`--r-full`), band-tinted soft background + band chip-text color. e.g. Critical = `#FFECEC` bg / `#C4303B` text. Includes a 6px dot in the orb gradient.

### Modal / popover
`--bg-surface`, `--r-xl`, `--shadow-lg`, 32px padding. Backdrop `rgba(28,27,26,.35)` with 4px blur.

### Source badges
Small rounded squares (`--r-sm`, 24px) carrying the source glyph (Gmail, Outlook, Slack, Jira, LinkedIn) on `--bg-subtle`. Muted, monochrome-friendly — context not decoration.

---

## 7. Iconography

- **Style:** Line icons, 1.75px stroke, rounded caps/joins (Lucide-style). Friendly, consistent optical weight.
- **Sizes:** 16 / 20 / 24px. Default color `--text-secondary`; active `--accent`.
- Avoid filled/duotone icons except brand source glyphs.

---

## 8. Motion

- **Durations:** micro 150ms, standard 200ms, entrance 250ms.
- **Easing:** `cubic-bezier(.2,.8,.2,1)` (gentle ease-out) for entrances/hovers; `ease-in-out` for toggles.
- **Hover lift:** translateY(−1px) on cards/CTAs.
- **Orb:** a slow, barely-there breathing pulse on the ambient shadow for the single top-priority item only. Everything else is still.
- **Respect `prefers-reduced-motion`** — disable pulse and translate.

---

## 9. Page Inventory (mockups in this folder)

| File | Screen |
|---|---|
| `01-landing-hero.png` | Marketing hero |
| `02-landing-features-pricing.png` | Features showcase + 4-tier pricing |
| `03-dashboard.png` | App dashboard, bento grid, priority orbs |
| `04-billing.png` | Billing / 4-tier plans + usage meters |
| `05-admin-tuning.png` | Admin AI tuning interface |
| `06-auth.png` | Login / signup |

---

## 10. Handoff notes for Frontend

- Tokenize everything above as CSS custom properties (`:root`) — names match this doc.
- This is a **light-first** system. There is no dark mode requirement in v2; ship light only.
- Load Satoshi (or swap to Inter everywhere if licensing is a blocker — the scale still holds).
- Priority color is the *only* semantic color in the product surface; keep chrome neutral.
- All interactive surfaces need visible focus states (accent ring) for WCAG 2.1 AA. Verify text contrast ≥ 4.5:1 (`--text-secondary` on `--bg-canvas` passes).
