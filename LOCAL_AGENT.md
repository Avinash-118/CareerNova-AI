# Local extension-free application assistant

Run these in two PowerShell terminals from the project directory.

Backend:

```powershell
$env:APP_ENV='development'
$env:COOKIE_SECURE='false'
$env:APPLICATION_ASSISTANT_ENABLED='true'
.\venv\Scripts\python.exe -m uvicorn backend:app --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
npm run dev --prefix frontend -- --host 127.0.0.1
```

Open http://127.0.0.1:5173/agent-demo for the local sample form. Sign in, save a Candidate Profile and upload a resume in Resume Library. Choose a saved resume and start the agent. This demo route is only included in the Vite development build; its sample form endpoint returns 404 in production.

For a real application, use the local Find jobs page, choose Apply with Nova, select the resume in the preparation panel, then Start application assistant. The agent opens a separate controlled Chromium window. Keep both windows open. If the page is an overview, open its Application tab and use Scan & fill saved details. Passwords, CAPTCHA, legal acknowledgements, eligibility answers and final submission require the user's attention. Missing answers can be entered or dictated and confirmed.

Supported text fields are matched conservatively. Custom dropdown selections must match a visible option exactly; ambiguous selections remain manual. Resume attachment is attempted only on recognized resume/CV fields with an explicitly selected saved version. The agent verifies retained values and the native file selection; this does not guarantee that an employer's asynchronous resume-processing service accepted the document. No applications are automatically submitted.

The public Vercel site still has no hosted remote-browser service. Running this local assistant does not enable the public site to control a laptop browser. It uses the local database configured in .env; it does not migrate live profiles or resumes.
