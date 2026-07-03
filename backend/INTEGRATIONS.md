# PriorityFlow Integrations Hub Architecture

This document outlines the architecture for integrating third-party communication platforms into PriorityFlow.

## 1. Platform Evaluation

| Platform | API / Protocol | Auth Type | Feasibility | Status | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Gmail** | Google Gmail API | OAuth2 | High | Implemented | Mature API. Use `watch()` for real-time push via Pub/Sub. |
| **Outlook** | MS Graph API | OAuth2 | High | Implemented | Consistent with other Microsoft services. Use Webhooks. |
| **Slack** | Slack Web/Events API | OAuth2 / Bot | High | Implemented | Use Events API for real-time delivery. |
| **WhatsApp** | WhatsApp Business API | API Key / OAuth | Medium | Implemented | Official API for businesses. Cloud API is easiest. |
| **MS Teams** | MS Graph API | OAuth2 | High | Implemented | Consistent with Outlook. Use Webhooks. |
| **Jira** | Jira REST API | OAuth2 / API Key | High | Implemented | Mature API for issues and comments. |
| **iMessage** | N/A | N/A | Very Low | Backlog | Restricted. No public API; sandbox environment has no Mac access. |

## 2. Unified Data Schema (Normalization)

All incoming communications must be transformed into this standard JSON format before being processed by the `AIAnalyzer` and `PriorityEngine`.

```typescript
interface NormalizedCommunication {
  id: string;              // Internal UUID
  source: string;          // 'gmail', 'slack', etc.
  external_id: string;     // ID from the source platform
  thread_id?: string;      // For grouping related messages
  sender: {
    name: string;
    handle: string;        // Email, username, or phone number
    avatar_url?: string;
  };
  recipient: string;       // The user's identifier on that platform
  subject?: string;        // Mostly for email
  content: string;         // Plain text content for AI analysis
  html_content?: string;   // Original HTML if available
  timestamp: string;       // ISO-8601 format
  deadline?: string;       // Extracted or explicitly set deadline
  source_url?: string;     // Link to view the original message
  metadata: Record<string, any>; // Platform-specific raw data
}
```

## 3. OAuth2 Flow Design

PriorityFlow uses a standard OAuth2 Authorization Code flow to manage third-party permissions.

1.  **Initiation**: Frontend sends a request to `/api/v1/auth/{provider}/connect`.
2.  **Redirection**: Backend returns the provider's Authorization URL with required scopes (e.g., `gmail.readonly`).
3.  **User Consent**: User signs in to the provider and grants access.
4.  **Callback**: Provider redirects to `https://api.priorityflow.com/auth/{provider}/callback?code=...`.
5.  **Token Exchange**: Backend exchanges the `code` for an `access_token` and a `refresh_token`.
6.  **Persistence**: Tokens are encrypted and stored in the database, linked to the User ID.
7.  **Polling/Webhooks**: 
    - **Polling**: A background worker (Celery/Redis) fetches updates using the `refresh_token`.
    - **Webhooks**: Platforms like Slack/GitHub push updates directly to our API.

## 4. Integration Hub Components

- **IntegrationManager**: Core service that coordinates all active integrations.
- **ProviderAdapters**: Individual modules for each platform (e.g., `GmailAdapter`, `SlackAdapter`) that handle authentication and data normalization.
- **WorkerPool**: Manages background fetching tasks to avoid blocking the main API.
- **SecretStore**: Handles encryption/decryption of OAuth tokens.

## 5. Slack Implementation Summary
- **Status**: Mock implementation complete.
- **Feasibility**: High.
- **Normalization**: Slack messages (DMs, mentions, and channel messages) are normalized.
- **Metadata**: Includes `channel_name`, `message_type`, and `is_urgent` flags.

## 6. WhatsApp Implementation Summary
- **Status**: Mock implementation complete.
- **Feasibility**: Medium.
- **Normalization**: Normalizes personal, group, and business messages.
- **Metadata**: Includes `chat_type`, `is_business`, and `phone_number`.

## 7. Outlook Implementation Summary
- **Status**: Mock implementation complete.
- **Feasibility**: High.
- **Normalization**: Standardizes Outlook emails including categories.
- **Metadata**: Includes `conversation_id`, `is_read`, and `categories`.

## 8. MS Teams Implementation Summary
- **Status**: Mock implementation complete.
- **Feasibility**: High.
- **Normalization**: Normalizes channel posts, direct chats, and mentions.
- **Metadata**: Includes `team_name`, `channel_name`, and `message_type`.

## 10. Data Privacy & Security

PriorityFlow implements multi-layered security to ensure user data remains private and secure:

- **Secret Management**: All third-party integration tokens (OAuth tokens, API keys) are encrypted at rest using `cryptography.fernet` (AES-128 in CBC mode with a 128-bit key for encryption; using HMAC with SHA256 for authentication).
- **AI Prompt Sanitization**: Before sending any communication content to external LLM providers (e.g., Google Gemini), a sanitization layer scrubs Personally Identifiable Information (PII) including email addresses, phone numbers, and sensitive identifiers.
- **Strict Multi-Tenancy**: Every database operation and API request is scoped by a `tenant_id`. Strict ownership verification ensures that users can only view or modify items belonging to their own organization.
