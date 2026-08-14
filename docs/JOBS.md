# Job Architecture

Jobs are persisted in `job_runs` with an idempotency key formed from job type, scope, and logical as-of timestamp. They record queue/start/completion time, attempt count, retry time, freshness evidence, status, and structured error information.

Initial states are `QUEUED`, `RUNNING`, `SUCCEEDED`, `PARTIAL`, `BLOCKED_STALE`, and `FAILED`. The foundation service provides idempotent enqueueing, start, success, and valuation freshness gating.

Future collection, reconstruction, report, and delivery jobs must use this boundary. A valuation/report job becomes `BLOCKED_STALE` if required price or FX input is stale. It must not be delivered as a current valuation report.
