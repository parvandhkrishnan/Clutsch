# Backend Scalability & Async Architecture

PriorityFlow has been enhanced to handle high concurrent loads and provide a responsive user experience even during heavy processing.

## 1. Async Background Workers
We have implemented a dedicated `BackgroundWorker` (in `worker.py`) that manages a pool of worker threads.
- **Decoupling**: Integration syncing and AI analysis are moved out of the main request-response cycle.
- **Task Queue**: A thread-safe queue handles pending tasks, ensuring the API remains responsive.
- **Monitoring**: Task status and results can be tracked via the `/worker/status/{task_id}` endpoint.

## 2. Distributed-Ready Caching
Caching is implemented using an extensible architecture. Currently, it uses a `SimpleTTLCache`, but it is designed to be easily swapped with Redis.
- **User Cache**: User objects and permissions are cached to avoid repeated database lookups.
- **Item Cache**: Normalized items from integrations are cached per tenant.
- **AI Cache**: AI analysis results are cached based on the hash of the sanitized content, avoiding redundant (and expensive) LLM calls.

## 3. Intelligent Retries
All third-party API calls are wrapped with exponential backoff retry logic.
- **Jitter**: Random jitter is added to avoid "thundering herd" problems.
- **Configurable**: Max retries and base delays are configurable per-provider.

## 4. Database Connection Pooling
The database layer now simulates a connection pool to manage concurrent data access efficiently.
- **Pool Size**: Configurable limit on concurrent "connections".
- **Blocking Acquisition**: Requests for connections block until one becomes available, preventing database exhaustion under heavy load.

## 6. Priority Auto-Tuning Feedback Loop
The system now includes a continuous learning loop that adjusts prioritization weights based on user interactions.
- **Feedback Collection**: Users can provide feedback on assigned priorities through dedicated endpoints.
- **Dynamic Weight Adjustment**: The system automatically adjusts semantic and entity weights (projects/clients) for the tenant when corrections are made.
- **Tenant Isolation**: All tuning adjustments are scoped to the specific tenant, ensuring that feedback from one organization doesn't affect another's prioritization logic.
- **Auditability**: Every auto-tuning event is logged in the audit trail for transparency.
