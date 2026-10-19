# Local Google, GitHub and Gmail setup

Use `http://localhost:5173` consistently when opening CareerNova. Run the commands below in PowerShell from this project folder. Secrets are entered in hidden prompts and stored only in the ignored `.env` file. Never paste them into chat or commit them.

## 1. Google sign-in

1. Open [Google Cloud Console](https://console.cloud.google.com/) and create or select a project.
2. Open Google Auth Platform. Complete Branding and Audience. For a personal development project, select External and add your Google account as a test user while the app is in testing.
3. Under Clients, create an OAuth client with application type **Web application**.
4. Set the authorized JavaScript origin to `http://localhost:5173`.
5. Set the authorized redirect URI to exactly `http://localhost:5173/api/auth/oauth/google/callback`.
6. Copy the client ID and client secret into the local helper prompts:

```powershell
.\venv\Scripts\python.exe configure_integrations.py --oauth google
```

Reference: [Google web server OAuth setup](https://developers.google.com/identity/protocols/oauth2/web-server).

## 2. GitHub sign-in

1. In GitHub, open Settings → Developer settings → OAuth Apps → New OAuth App.
2. Set application name to `CareerNova AI` and homepage URL to `http://localhost:5173`.
3. Set Authorization callback URL to exactly `http://localhost:5173/api/auth/oauth/github/callback`.
4. Register the application, then generate a client secret. Use the client ID and client secret, rather than a personal access token:

```powershell
.\venv\Scripts\python.exe configure_integrations.py --oauth github
```

Reference: [GitHub OAuth app creation](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/creating-an-oauth-app).

## 3. Gmail delivery

1. Open your Google Account → Security and enable **2-Step Verification**.
2. Open [App passwords](https://myaccount.google.com/apppasswords), name the app `CareerNova`, and create a password.
3. Enter the sending Gmail address and the generated 16-character App Password in the helper. Your normal Gmail password will not work. Spaces in the displayed App Password are accepted.

```powershell
.\venv\Scripts\python.exe configure_integrations.py --gmail
```

If App passwords is unavailable, Google documents restrictions for managed accounts, Advanced Protection, and some security-key-only setups. Use an eligible account or another SMTP provider instead.

Reference: [Google App Password instructions](https://support.google.com/accounts/answer/185833?hl=en).

## 4. Verify and run

Check credential presence without displaying secrets:

```powershell
.\venv\Scripts\python.exe configure_integrations.py --check
```

Restart the backend after saving credentials. Keep the frontend on port 5173 and complete each provider's login in your browser. Presence checks alone cannot prove OAuth works.

After setup, tell the assistant “credentials saved” so it can verify the configuration and send the single authorized test notification. SMTP acceptance still requires checking the recipient inbox or spam folder to confirm receipt.

For ongoing job alerts, users must verify their account email, enable email digests and create an alert rule. Run the alert worker in a separate terminal alongside the backend:

```powershell
.\venv\Scripts\python.exe alert_worker.py
```

Leave that process running for periodic alerts. A local worker stops when its terminal or computer shuts down; continuous delivery requires an always-running deployment.
