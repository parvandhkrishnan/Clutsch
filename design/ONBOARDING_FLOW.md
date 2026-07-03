# PriorityFlow Onboarding User Flow

## Overview
The onboarding experience is designed to get the user from registration to their first "prioritized moment" as quickly as possible. We use a high-focus, guided approach to minimize friction during initial setup.

## Flow Steps

### 1. Welcome & Vision
- **Screen:** `onboarding-welcome.png`
- **Goal:** Reiterate the value proposition and create a sense of focus.
- **Action:** Primary button "Get Started" transitions to Integration setup.

### 2. Guided Integration (The "Critical Path")
- **Screen:** `onboarding-integration-guided.png`
- **Goal:** Connect at least one high-signal source (Gmail or Slack).
- **Process:**
    - User selects a service (e.g., Gmail).
    - Opens OAuth modal (designed in `linkedin-connect-modal.png` but generalized).
    - **Success State:** Once connected, the UI shows a "Fetching & Prioritizing..." loading state to build anticipation.

### 3. Personalization (AI Tuning)
- **Goal:** Fine-tune the AI ranking based on user intent.
- **Input:** A quick 3-question survey:
    - "Who are your most important stakeholders?" (e.g., Clients, Executive Team).
    - "What's your primary focus today?" (e.g., Project X, Urgent Support).
    - "Which platforms do you use most for critical work?"

### 4. Interactive Dashboard Tour
- **Screen:** `onboarding-dashboard-tour.png`
- **Goal:** Explain the core UI components using demo data.
- **Tour Points:**
    1. **The Priority Score:** Explaining the 0-100 logic.
    2. **Smart Insights:** Highlighting the "Why" (e.g., "AI detected a deadline in this message").
    3. **Focus Panel:** Showing the 3rd column for deep work and quick actions (Reply, Delegate, Snooze).

### 5. Completion & Real-Time Sync
- **Goal:** Transition from demo data to the user's actual live feed.
- **Action:** Final CTA "Start Focusing".
- **Outcome:** Land on the main dashboard with the user's first batch of prioritized items.

## Design Principles for Onboarding
- **Zero Distraction:** Use dark overlays to focus the user's eye on the current step.
- **Immediate Gratification:** Show the user their data being processed and ranked immediately after connection.
- **Guided Confidence:** Never leave the user wondering "what's next".
