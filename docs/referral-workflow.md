# Referral Outreach Workflow

`n8n/workflows/07-referral-outreach.json` is the dedicated Warm Reach workflow. It is separate from the existing job-email workflows, so importing it does not replace or interrupt them.

The workflow accepts a contact, relationship context, and optional company or opportunity. It creates or reuses the local referral ask, retrieves local memory, asks Ollama for four small email parts, assembles the fixed greeting and signature, creates a Gmail draft, then saves the generated subject and body back to the referral ask.

It never sends the email.

## Import and Configure

1. In n8n, choose **Import from File** and select `n8n/workflows/07-referral-outreach.json`.
2. Open **Create Referral Gmail Draft** and select the Gmail OAuth credential already used for drafts.
3. Leave the workflow inactive. It runs only when called manually or from a later Warm Reach action.
4. In **Workflow Input**, replace the example values with the person and referral context. **Save Referral Ask** creates or reuses the local Warm Reach ask before drafting, so no internal ID is needed.
5. Execute the workflow manually. Inspect the Gmail draft and the saved draft status before sending anything yourself.

## Required Input

```json
{
  "contact_name": "Person's name",
  "contact_email": "person@example.com",
  "company": "Optional target company",
  "opportunity": "Optional role, team, or introduction",
  "relationship_context": "How you know the person",
  "ask_context": "What you want to ask"
}
```

The workflow uses the supplied facts only. Its generated pieces are deliberately short: subject, opening, optional relationship point, and a no-pressure referral question. The greeting and `Best,\nPruthvi Kadam` signature are fixed boilerplate.
