# Clutsch UI Redesign v2 — Fillout-Inspired

Clean, light, approachable redesign of the Clutsch product and marketing surfaces.
Replaces the v1 dark/dense identity with a warm off-white, whitespace-heavy aesthetic
inspired by Fillout.com (primary), Linear, Notion, Raycast, and Superhuman.

## Contents

| File | What it is |
|---|---|
| `DESIGN_SYSTEM.md` | **Start here.** Full design system — color tokens, type scale, spacing, radii, shadows, components (buttons, cards, inputs, priority orb, chips, modals), iconography, motion, and frontend handoff notes. |
| `01-landing-hero.png` | Marketing hero — nav, display headline, dual CTA, floating product preview. |
| `02-landing-features-pricing.png` | Feature showcase (3 cards) + 4-tier pricing (Free / Pro / SME / Enterprise). |
| `03-dashboard.png` | App dashboard — slim sidebar + bento grid, priority inbox rows, priority orbs, spotlight & stat cards. |
| `04-billing.png` | Billing page — current plan, usage meters, 4-tier comparison, billing history. |
| `05-admin-tuning.png` | Admin AI priority tuning — semantic/contextual/entity sliders + live re-rank preview. |
| `06-auth.png` | Login / signup split screen with SSO options. |

## Design direction (one-liner)
Warm off-white canvas (`#FAFAF9`), white cards with soft shadows + 1px borders + rounded 16–24px corners,
electric violet (`#6C3BFF`) as the single confident accent on light, and **priority color reserved
exclusively for the orbs/score chips** so the rest of the chrome stays calm. Friendly Satoshi-style
display type, generous whitespace, motion that reassures (150–250ms ease-out).

## For the frontend engineer
`DESIGN_SYSTEM.md` §10 has the handoff notes. This is a **light-first** system — no dark mode in v2.
Tokenize the palette/type/spacing as CSS custom properties (names in the doc match 1:1). The priority
orb is the one component where color carries meaning; everything else is neutral.

_Superseded v1 assets live one level up in `../` and in `../redesign/`._
