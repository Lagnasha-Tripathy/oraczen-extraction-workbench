# Design Decisions

## Simple Architecture

The project intentionally uses a simple architecture because the assignment focuses on extraction, validation, retries, and human review.

## In-Memory Storage

In-memory storage is used because the assignment contains 150 tickets and does not require persistent storage. This keeps the setup simple and avoids unnecessary infrastructure.

## Deterministic Mock Provider

A deterministic mock provider is used so the application can run without API keys or external services. It also makes validation failures and retry scenarios predictable during testing.

## Validation and Retry

Every extraction result is validated using Pydantic. If validation fails, the system retries exactly once using the validation error as feedback. If the second attempt also fails, the record is moved to `needs_review`.

## Concurrency

`asyncio.Semaphore` is used to limit the number of tickets processed concurrently. The limit is configurable through `MAX_CONCURRENCY`.

## Polling

The frontend polls the backend for job progress instead of using WebSockets. This keeps the implementation simple while still providing near real-time progress updates.

## Human Review

Records that fail extraction twice are sent to human review. Human edits use the same validation schema as model-generated data so that manually corrected records follow the same rules.

## No External Infrastructure

The project does not use a database, Redis, Docker, message queue, or external LLM service because these are not required for the assignment.