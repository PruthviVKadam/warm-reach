# Gmail

Use a separate Gmail OAuth2 credential in n8n for every inbox. Do not put the Google OAuth client secret in `.env` or workflow JSON. The [credential and first-run guide](credentials.md#gmail-oauth2-for-the-gmail-trigger-and-drafts) gives the exact Google Cloud and n8n steps.

Start with monitoring and draft creation. This project creates outreach as Gmail drafts; it does not automatically send them. The email monitoring workflow ignores newsletters and generic marketing email.
