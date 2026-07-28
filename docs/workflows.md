# Workflows

Workflow exports live in `n8n/workflows`.

Import the six legacy job-email workflow JSON files when you need that automation:

1. `01-email-monitoring.json`
2. `02-recruiter-research.json`
3. `03-email-drafting.json`
4. `04-crm-updates.json`
5. `05-reminder-engine.json`
6. `06-daily-report.json`

For Warm Reach referral drafts, import `07-referral-outreach.json` separately and follow [referral-workflow.md](referral-workflow.md). It creates a Gmail draft and records it against a saved referral ask; it does not send email.

For inbox reply candidates, import `08-referral-reply-monitor.json` separately and follow [reply-monitoring.md](reply-monitoring.md). It starts inactive and never sends mail or automatically marks a referral outcome.

After importing, run this from the project directory before testing or activating `01 Email Monitoring`:

```powershell
.\scripts\repair_n8n_subworkflow_links.ps1
```

n8n assigns new IDs when workflows are imported through the editor. The repair command exports the six local workflows, binds the three Execute Sub-workflow nodes in `01 Email Monitoring` to the actual IDs, and updates only that parent workflow. It keeps a temporary full-workflow backup inside the n8n container. If the parent workflow is active, the script stops without changing it; deactivate it first, rerun the command, review the repaired workflow, then reactivate it. Reload the n8n editor after the command so it displays the saved references.

After import:

- Open every Gmail, SMTP, and notification node and select your own credentials.
- Keep every send step behind approval.
- Run each workflow manually with sample data before activating triggers.
- Use n8n execution logs to inspect retries and failures.
