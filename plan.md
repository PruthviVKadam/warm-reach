# Plan

## Gate 0: Start Approval

Status: Green

Evidence: User requested "go ahead and code it according the the prompt" on 2026-07-27.

## Phase 1: Runnable Local Scaffold

Goal: Create the project structure, Docker Compose stack, environment template, prompts, docs, and database schema needed to run the platform locally.

Gate: Green

Evidence: Added Docker Compose, `.env.example`, prompts, docs, folder structure, and SQLite schema. No real credentials were added.

## Phase 2: Tested Custom Helpers

Goal: Add custom scripts for email classification normalization, recruiter ranking, follow-up scheduling, SQLite CRM setup, and workflow JSON validation.

Gate: Green

Evidence: `python -m unittest` passed 14 tests.

## Phase 3: Modular n8n Workflows

Goal: Provide importable sample workflow exports for email monitoring, recruiter research, email drafting, CRM updates, reminders, and daily reports.

Gate: Green

Evidence: Workflow exports validate through `tests/test_workflows.py`; `python -m unittest` passed 31 tests after adding company-presence guards, an explicit CRM input contract, parent-to-CRM field mappings, pinned walkthrough data, valid recruiter-array JSON serialization, local RAG compatibility coverage, boilerplate-email composition coverage, and Gmail-notification guard coverage. Controlled local CRM, recruiter-ranking, memory-retrieval, and draft-generation endpoint checks also succeeded, including draft generation from inside the n8n container using `qwen3:4b`. The inactive live email-drafting workflow was read back after the boilerplate-node import, its assembly code ran successfully against a controlled fixture without creating a Gmail draft, and its Gmail approval-notification node was confirmed to have the working credential plus a configured recipient. The live Email Monitoring SMTP notification was also read back after restart with its attached credential and configured recipient expression.

## Phase 4: Live Credential Wiring

Goal: Configure Gmail OAuth, SMTP, and live n8n credentials.

Gate: Green

Evidence: Gmail and SMTP credentials were configured in n8n, and the user confirmed the n8n workflow is working end to end on 2026-07-28.

## Phase 5: Dashboard Buildout

Goal: Build dashboard screens for applications, recruiters, timelines, response rate, follow-ups, and notes.

Gate: Green

Evidence: The core n8n workflow is now running. The user explicitly requested continued application development on 2026-07-28.

Initial delivery: Added the built-in local Recruiting Operations dashboard at `http://localhost:8087/dashboard` with application metrics, search/status filters, status updates recorded in the timeline, suggested follow-ups, and recent activity. `python -m unittest` passed 32 tests; the rebuilt worker served the HTML, CSS, JavaScript, and CRM API successfully; desktop/mobile browser QA found no console errors. Recruiter, response-rate, and note-management views remain the next dashboard increment.

## Phase 6: Warm Reach Referral-First Refactor

Goal: Reframe the product as a personal platform for thoughtful referral outreach by adding referral contacts, referral asks, relationship context, drafts, replies, and follow-ups as the primary model.

Gate: Green

Evidence: User explicitly changed the product direction and approved continued coding on 2026-07-28. Existing application records were preserved rather than converted into unsupported referral history. Added referral contacts, asks, activity, follow-up and status APIs, the Warm Reach dashboard, and the inactive live `07 Referral Outreach` n8n workflow. The workflow uses the existing Gmail draft credential, creates drafts only, and saves draft details to the related referral ask. `python -m unittest` passed 36 tests; Compose validation, worker/n8n health checks, endpoint checks, and desktop browser QA all passed. No referral workflow execution, Gmail draft, or email send was performed during verification.

## Phase 7: Referral Reply Monitoring and Ranking

Goal: Monitor replies from the Gmail inbox for referral asks marked sent, correlate inbound mail to the known contact and sent ask, store reply evidence, rank reply likelihood from least to most likely, and show the ranked list in Warm Reach for review.

Gate: Green

Guardrails: Do not treat a message as a referral reply based only on a weak match. Preserve the source message metadata and confidence, require review for ambiguous matches, and do not send messages or change an ask to referred automatically.

Evidence: Added per-ask referral reply-candidate storage, explainable matching against sent asks, candidate review states, dashboard ranking from least to most likely, and the inactive live `08 Referral Reply Monitor` workflow. It reuses the existing Gmail credential, polls unread mail only when activated, and calls only the local matching API. `python -m unittest` passed 39 tests; Compose validation, worker/n8n/Crawl4AI health checks, safe validation-error endpoint checks, live n8n export readback, and desktop browser QA all passed. Crawl4AI now has a local token and n8n reaches it over the Docker network. Both referral workflows remain inactive; no inbox mail was read during verification.
