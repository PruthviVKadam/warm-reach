# Credentials and First Run

This guide configures the credentials needed by the local Warm Reach stack. It does not ask you to put Google or SMTP secrets in workflow JSON. n8n stores those secrets in its encrypted credential store.

## What Needs a Credential

| Item | Where it is entered | Needed now | What it does |
| --- | --- | --- | --- |
| n8n encryption key | `.env` | Yes | Encrypts credentials saved by n8n. |
| n8n owner account | n8n first-run page | Yes | Signs in to the local n8n interface. |
| Gmail OAuth client ID and secret | n8n Gmail OAuth2 credential | Yes for inbox monitoring and Gmail drafts | Lets the Gmail Trigger read the authorized inbox and lets the drafting workflow create a draft. |
| SMTP username and app password | n8n SMTP credential | Yes for follow-up and daily-report notifications | Sends SMTP-based reminder and report notifications. |
| `SMTP_FROM_EMAIL`, `SMTP_FROM_NAME`, and `NOTIFICATION_EMAIL` | `.env` | Yes if notifications are enabled | Configures notification senders and the recipient for the Gmail approval notice. |
| `CRAWL4AI_API_TOKEN` | `.env` | Yes if Crawl4AI is used | Allows trusted Docker services to call the local Crawl4AI API. |
| Hunter, Apollo, RocketReach API keys | `.env` | No | Reserved for a future, authorized contact-discovery integration. The shipped workflows do not call these APIs. |

Ollama, Qdrant, SearXNG, Crawl4AI, SQLite, and Appsmith run as local Docker services in this project. They do not need API keys for this local setup.

## 1. Create the Local `.env` File

1. In PowerShell, run this command from the project directory:

```powershell
Copy-Item .env.example .env
```

2. Generate a stable 64-character encryption key:

```powershell
([guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N'))
```

3. Open `.env` and replace only the placeholder value after `N8N_ENCRYPTION_KEY=` with the generated value. Keep that key in a password manager. Do not change it after creating n8n credentials; n8n needs the same key to decrypt them later.

4. For a local-only setup, keep these values unchanged:

```dotenv
N8N_PORT=5678
N8N_PROTOCOL=http
N8N_HOST=localhost
N8N_WEBHOOK_URL=http://localhost:5678/
```

5. Fill in the notification sender values. With Gmail SMTP, both values can use the same Gmail address:

```dotenv
SMTP_FROM_EMAIL=your.address@gmail.com
SMTP_FROM_NAME=Your Name
NOTIFICATION_EMAIL=your.address@gmail.com
```

6. Leave `HUNTER_API_KEY`, `APOLLO_API_KEY`, and `ROCKETREACH_API_KEY` blank. They are optional and have no effect until a future workflow adds an authorized API call.

7. Generate a local Crawl4AI API token and add it to `.env` when Crawl4AI is enabled:

```powershell
([guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N'))
```

Set the resulting value as `CRAWL4AI_API_TOKEN`. This lets trusted containers reach Crawl4AI while keeping its HTTP API protected from unauthenticated requests.

Do not add a Gmail password, Google OAuth client secret, or SMTP app password to `.env`. Those are entered in n8n after it starts.

The included workflow exports resolve local service URLs and notification settings with `$env`. Docker Compose allows that only for this local instance. Import and run only workflows you trust, because a workflow that can read `$env` can also inspect values available to the n8n container.

## 2. Start n8n and Create the Owner Account

1. Start Docker Desktop and wait until it reports that the engine is running.

2. From the project directory, start the services:

```powershell
docker compose up -d
```

3. Open `http://localhost:5678`.

4. At the first-run screen, create an n8n owner account with an email address you control and a unique password. Store that password in a password manager.

5. Do not look for an HTTP Basic Auth prompt. Modern n8n uses the owner-account screen; the retired `N8N_BASIC_AUTH_*` environment variables are not part of this project.

6. Before connecting email, import the six JSON files in `n8n/workflows`, then run `.\scripts\repair_n8n_subworkflow_links.ps1` as described in [workflows.md](workflows.md). Imported workflows do not contain your secrets.

## 3. Gmail OAuth2 for the Gmail Trigger and Drafts

Use this path if you want the `Gmail Trigger` to monitor an inbox and `Create Gmail Draft` to create drafts in that inbox. This requires a Google Cloud OAuth client, not a Google API key. n8n's current self-hosted OAuth guide confirms the required flow: Google Cloud project, Gmail API, consent screen, OAuth client, then the n8n credential. See [n8n's Google OAuth2 guide](https://docs.n8n.io/integrations/builtin/credentials/google/oauth-single-service) and [Google's Gmail authorization guide](https://developers.google.com/workspace/gmail/api/auth/web-server).

### 3.1 Start the n8n Credential First

1. In n8n, select **Credentials** from the left sidebar.

2. Select **Create Credential** and search for **Gmail OAuth2 API**.

3. Choose the custom OAuth2 setup used by self-hosted n8n.

4. Copy the displayed **OAuth Redirect URL** and keep the n8n tab open. For this local project it is normally:

```text
http://localhost:5678/rest/oauth2-credential/callback
```

Copy the actual value from n8n rather than typing it. The protocol, host, port, and path must match Google Cloud exactly.

### 3.2 Create or Select a Google Cloud Project

1. Open [Google Cloud Console](https://console.cloud.google.com/).

2. Use the project picker in the header. Select an existing personal project or choose **New Project**.

3. Give it a recognizable name, such as `warm-reach-local`, and create it.

4. Confirm that project is selected in the header before continuing. Google credentials and APIs are created per project.

### 3.3 Enable the Gmail API

1. In Google Cloud Console, open **APIs & Services** > **Library**.

2. Search for **Gmail API**.

3. Open **Gmail API** and select **Enable**.

This is required even though the OAuth client is created in the same Google Cloud project.

### 3.4 Configure the Google Auth Platform

1. Go to **Google Auth Platform** > **Overview**. If it has not been configured, select **Get started**.

2. Enter an app name, such as `Warm Reach Local`.

3. Choose your Google account for **User support email**.

4. For a personal Gmail account, choose **External**. For a managed Google Workspace account where only people in that organization need access, choose **Internal**.

5. Enter a developer contact email address, accept the Google API Services User Data Policy, and create the configuration.

6. If you chose **External**, open **Audience** and add the Gmail address you will authorize as a test user. In Testing mode, only listed test users can finish the OAuth sign-in.

7. For local `localhost` use, leave **Authorized domains** empty. If you later expose n8n through a public domain, add and verify that domain before using it in OAuth.

### 3.5 Create the OAuth Client ID and Secret

1. Go to **Google Auth Platform** > **Clients**.

2. Select **Create client**.

3. Choose **Web application**.

4. Give it a name such as `n8n local Gmail`.

5. Under **Authorized redirect URIs**, choose **Add URI** and paste the exact OAuth Redirect URL copied from n8n.

6. Select **Create**.

7. Copy the resulting **Client ID** and **Client secret**. The client secret is sensitive. Do not download it into this repository or put it in `.env`.

### 3.6 Finish the Gmail Credential in n8n

1. Return to the open Gmail OAuth2 credential in n8n.

2. Paste the Client ID into **Client ID** and the client secret into **Client Secret**.

3. Select **Sign in with Google**.

4. Sign in to the inbox that n8n should monitor. Confirm that the account is the same one listed as a test user when the consent screen is in Testing mode.

5. Review Google's requested Gmail permissions, select **Allow**, then save the credential in n8n with a clear name, such as `Gmail - Warm Reach`.

6. Open `01-email-monitoring` and select this credential in the **Gmail Trigger** node.

7. Open `03-email-drafting` and select the same credential in the **Create Gmail Draft** node.

8. Save both workflows. Keep the workflows inactive until the manual checks in step 5 pass.

### Gmail OAuth Troubleshooting

| Problem | Likely cause | Fix |
| --- | --- | --- |
| `redirect_uri_mismatch` | Google Cloud has a different callback URL. | Copy the redirect URL from the n8n credential again and replace the Google Cloud URI exactly. |
| Access denied or app not verified | The OAuth app is External and the Gmail account is not a test user. | In Google Auth Platform > Audience, add that Gmail account as a test user. |
| `invalid_client` | Client ID or secret was copied incorrectly or belongs to another Google Cloud project. | Copy both values again from the same OAuth client and re-enter them in n8n. |
| Gmail API error | Gmail API was not enabled in the selected project. | Enable Gmail API under APIs & Services > Library, then reconnect the credential. |

## 4. SMTP for Notifications and Daily Reports

SMTP is used by the reminder and daily-report notifications. The email-drafting workflow creates Gmail drafts and uses its existing Gmail OAuth credential for its optional approval notice; it does not send outreach automatically.

For a personal Gmail inbox, use a Gmail app password. Google requires 2-Step Verification before it lets you create one, and recommends OAuth where the application supports it. The SMTP credential in this project uses SMTP, so an app password is the appropriate Gmail option. See [Google's App Password help](https://support.google.com/mail/answer/185833) and [Google Workspace SMTP settings](https://support.google.com/a/answer/176600).

### 4.1 Create a Gmail App Password

1. Sign in to the Google account that will send notifications.

2. Open [Google Account Security](https://myaccount.google.com/security).

3. Under **How you sign in to Google**, enable **2-Step Verification** if it is not already enabled.

4. Open [App passwords](https://myaccount.google.com/apppasswords). You may need to authenticate again.

5. Create a new app password with a recognizable name such as `n8n local notifications`.

6. Copy the 16-character password when Google displays it. Google does not show the same value again.

7. Do not store it in `.env`, workflow JSON, notes, screenshots, or this repository.

If the App passwords option is absent, the account may be a managed Workspace account, use Advanced Protection, or have a 2-Step Verification configuration that does not permit app passwords. In that case, ask the Workspace administrator for an approved SMTP method or use another SMTP provider you are authorized to use.

### 4.2 Create the n8n SMTP Credential

1. In n8n, go to **Credentials** > **Create Credential** and choose **SMTP**.

2. For Gmail, enter:

| n8n field | Value |
| --- | --- |
| Host | `smtp.gmail.com` |
| Port | `465` |
| SSL/TLS | Enabled |
| User | Full Gmail address, for example `your.address@gmail.com` |
| Password | The Gmail app password from step 4.1 |

3. Save it as `SMTP - notifications`.

4. If the n8n SMTP credential screen uses STARTTLS instead of an SSL/TLS switch, use port `587` and enable STARTTLS. Do not enable an implicit SSL connection on port `587`.

5. Open each workflow and select the `SMTP - notifications` credential in these nodes:

| Workflow | Node |
| --- | --- |
| `01-email-monitoring` | `Notify Me` |
| `05-reminder-engine` | `Notify Follow-up` |
| `06-daily-report` | `Email Report` |

6. Confirm `.env` contains the same sender address in `SMTP_FROM_EMAIL`. For `03-email-drafting`, set `NOTIFICATION_EMAIL` to the inbox that should receive approval notices. Its Gmail notification is skipped when neither value is configured, so the Gmail draft can still be created without a notification failure.

## 5. Verify Before Activating Triggers

1. Confirm `.env` still has no client secret, app password, or API key from n8n credentials.

2. Restart n8n after `.env` changes:

```powershell
docker compose up -d
```

3. In n8n, run `03-email-drafting` with controlled sample data. Confirm it creates a Gmail draft and, when `NOTIFICATION_EMAIL` is set, sends an approval notification through the same Gmail OAuth credential.

4. Run `06-daily-report` manually. Confirm that it sends only to `SMTP_FROM_EMAIL`.

5. Inspect the n8n execution details after each run. Fix any credential error before switching on a schedule or the Gmail Trigger.

6. Activate `01-email-monitoring` only after confirming that it monitors the intended inbox. Its outreach path ends with a Gmail draft for your review, not an automatic send.

## 6. Optional Contact-Discovery Keys

These variables are placeholders. Keep them blank until you add an authorized contact-discovery step to a workflow and understand the provider's terms, data source, and intended use.

| Variable | Where to find it | Store it |
| --- | --- | --- |
| `HUNTER_API_KEY` | Sign in to Hunter, then open **Account** > **API**. [Hunter's API guide](https://help.hunter.io/en/articles/1970956-hunter-api) describes the account API section. | `.env` only |
| `APOLLO_API_KEY` | In Apollo, open **Settings** > **Integrations** > **API** > **API keys**, then create a key. [Apollo's API guide](https://knowledge.apollo.io/hc/en-us/articles/4416173158541-Use-Apollo-API) covers API access. | `.env` only |
| `ROCKETREACH_API_KEY` | Sign in to RocketReach, open **Account** > **API Usage & Settings**, then generate or copy the API key. [RocketReach API](https://rocketreach.co/api) is the provider's API entry point. | `.env` only |

After editing `.env`, restart the relevant Docker services with `docker compose up -d`. Never paste an API key into a workflow export; use an environment variable or an n8n credential instead.
