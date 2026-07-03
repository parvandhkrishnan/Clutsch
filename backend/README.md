# PriorityFlow Backend

## Authentication & Multi-tenancy

PriorityFlow uses a custom multi-tenant authentication system based on JWT (JSON Web Tokens).

### Features
- **Multi-tenancy**: All items and integrations are scoped by `tenant_id`.
- **JWT Auth**: Stateless authentication using signed tokens.
- **Enterprise SSO**: Simulated SAML/OIDC flow for enterprise customers.
- **MFA Support**: User models include MFA configuration flags.

### Endpoints

#### `POST /auth/login`
Authenticates a user with username and password.
**Parameters**: `username`, `password` (Form data).
**Returns**: `access_token`, `token_type`.

#### `POST /auth/sso/login`
Simulates an Enterprise SSO login.
**Body**: `{"email": "user@company.com", "provider": "okta"}`.

### Securing Requests
All prioritized item endpoints now require a valid `Authorization: Bearer <token>` header. The system automatically scopes results to the user's tenant.

---

## Prioritization Engine v1

This module implements the core prioritization logic for PriorityFlow.

## Logic Overview

The algorithm calculates a `priorityScore` between 0 and 100 for each item, categorized into a `priorityTier`.

### Formula
```
BaseScore = (Urgency * W_u) + (Importance * W_i) + (SenderRank * W_s) + (DeadlineFactor * W_d)
FinalScore = BaseScore * SourceMultiplier
priorityScore = min(100, FinalScore * 100)
```

### Components
1.  **Urgency (0.0 - 1.0)**: AI-detected intent + Source-specific boosts (e.g., Personal WhatsApp).
2.  **Importance (0.0 - 1.0)**: AI-detected impact + Source-specific boosts (e.g., Jira Bug report).
3.  **Sender Rank (0.0 - 1.0)**: 1.0 (VIP) to 0.1 (Unknown).
4.  **Deadline Factor (0.0 - 1.0)**: Proximity to deadline (0.0 if none).

### Source Signals (Multipliers & Boosts)
- **Slack**: 1.1x for DMs, 1.2x for explicit urgent flag.
- **Jira**: 1.25x for "Highest" priority, 1.15x for "High", +0.1 Importance for bugs.
- **Teams**: 1.15x for direct @mentions.
- **Outlook**: 1.2x for "Urgent" category.
- **WhatsApp**: +0.1 Urgency for personal chats.

### Priority Tiers
- **Urgent**: >= 80
- **High**: >= 60
- **Medium**: >= 30
- **Low**: < 30

## API Reference

### Endpoints

#### `GET /priorities/feed`
Returns a unified, ranked list of items across all connected integrations.

**Parameters:**
- `provider` (optional): Filter by source (e.g., `slack`, `jira`).
- `tier` (optional): Filter by tier (e.g., `urgent`, `high`).
- `limit`: Number of items per page (default 20).
- `offset`: Pagination offset (default 0).

**Response Schema:**
```json
{
  "items": [
    {
      "id": "item-id",
      "text": "Message content",
      "source": "Slack",
      "priorityScore": 85.5,
      "priorityTier": "urgent",
      "explanation": "Production outage detected. Direct Message from colleague.",
      "source_url": "...",
      "metadata": { ... }
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0
}
```

#### `GET /items`
Legacy endpoint. Returns sorted items list without pagination wrapper. Includes `priorityScore`, `priorityTier`, and `explanation` for each item.

#### `POST /items`
Adds a new item to the in-memory database.

## Running the Server
```bash
python3 main.py
```
Default URL: `http://localhost:8001`
