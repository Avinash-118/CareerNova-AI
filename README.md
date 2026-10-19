# CareerNova AI

React/Vite frontend and FastAPI/PostgreSQL backend. Existing live/historical discovery, FAISS resume matching, candidate profiles and local Nova Playwright assistance are preserved. Existing uncommitted repository changes were retained.

## Run locally (PowerShell)

From the repository root:

```powershell
.\venv\Scripts\python.exe -m uvicorn backend:app --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open the printed Vite URL. The development `/api` proxy forwards to port 8000. Keep the same hostname throughout so session cookies work. Startup performs additive table/column migrations; back up PostgreSQL before deployment. Existing shared demo records are preserved without assigning them to registered users.

For a fresh environment:

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m playwright install chromium
```

Keep your existing `.env`. For a new setup, copy `.env.example` and supply PostgreSQL credentials. A valid `DATABASE_URL` takes precedence; otherwise the local settings use database `careernova_db`. Keep the ignored `jobs_metadata.parquet` and `jobs_faiss.index` in the repository root. Sentence-transformers needs its model cached or downloaded for semantic search.

## Career workspace

- Registration/login, password recovery, Argon2 password hashes, and revocable eight-hour HttpOnly SameSite=Lax cookie sessions. Password reset uses a hashed, single-use 30-minute token and revokes existing sessions.
- Per-account profiles, saved jobs, dashboard statistics, status/notes tracking and a drag-and-drop application board. Status menus offer a keyboard/touch alternative.
- Resume library: up to ten private PDF/DOCX versions per user, 5 MB each. Download, delete, match, or select a version per application. Nova can upload a selected stored version when it reaches a file question.
- Resume coaching: recognized missing skills, structure checks and bullet templates. Replace outcome placeholders with verifiable facts. Coaching/practice use transparent skill-based templates rather than an external generative service.
- Match explanations: actual embedding similarity, skill coverage and the existing 70% semantic / 30% skill formula. Scores are ranking aids, not hiring-eligibility assessments.
- Interview studio with role/skill-specific guided questions, editable answers and saved sessions.
- Interview, deadline and follow-up reminders, optionally linked to an application; local-time display and completion controls.
- Side-by-side comparison of up to four saved roles using company, location, compensation, match, stage and requirements. Missing information remains marked unknown.
- Free in-app alert rules with pause/resume/delete, deduplicated matches and mark-read. Verified users may opt into daily email digests and upcoming reminder emails.
- Google/GitHub sign-in with authorization-code PKCE flows, one-time browser-bound state and explicit account linking. Existing accounts are never silently linked by email.
- Listing reports, personal report history and manual employer-domain reviews with public evidence. Reviews are not safety guarantees.
- Privacy controls: export records/resume text, download original resumes, review/revoke sessions and delete an account after password confirmation or recent provider sign-in.
- Verified, allowlisted administrators can review reports/domains, inspect counts/feed health/worker activity/email status, check feeds and retry failed mail.

Open **Career tools** for the workspace pages. Dashboard and Settings provide related shortcuts. Authentication protects both workspace routes and backend features.

## Saved searches and duplicate detection

Save up to 30 named filter combinations from Job Discovery: keywords, career field, location, employment type, work arrangement and live/historical source. Restore/update combinations using the selector, or rename/run/remove them under **Career tools > Saved searches**. Historical searches receive the correct work-mode parameter.

Live-feed copies with the same canonical posting URL, normalized title and company are combined while retaining their source listing IDs. Known tracking parameters are removed, while requisition query IDs, path case and meaningful URL fragments are retained. Similar titles/company/location on different URLs remain separate and receive a possible-duplicate hint. Uncertain openings are kept rather than automatically merged.

Job cards show only the signed-in user's tracking stage when an exact ID or canonical posting match is found. Saving a clear duplicate returns the existing tracked entry without overwriting its notes/stage. Resume-match results and alerts use the same identity logic. Historical dataset rows are preserved individually; their personal tracking badges still use canonical identity.

## Application timeline

Open **Timeline** in navigation or **View activity** on a tracked application. Saves, stage transitions, note edits and application detail changes record activity in the same database transaction. Repeated saves and unchanged updates do not duplicate history. Add recruiter replies, interviews, submissions, offers, follow-ups and notes with the date they actually happened. Manual entries can be removed; automatic history remains until its application is deleted. Filtering and chronological cursor pagination support long histories, including backdated entries.

Existing opportunities receive one baseline event using their original saved timestamp. Earlier stage transitions are not fabricated. Saved searches/history are account-owned, included in data export and deleted with the account. Deleting an application also removes its timeline.

## Background worker and email

After starting the API once to initialize the schema, run a third terminal:

```powershell
.\venv\Scripts\python.exe alert_worker.py
```

Use `alert_worker.py --once` for one cycle. The worker runs every 15 minutes by default (`ALERT_CHECK_SECONDS`, minimum 60 seconds). A PostgreSQL advisory lock avoids overlapping cycles. Keep it running under your own service/process manager for unattended operation; no system service is installed automatically.

Set `SMTP_HOST`, `SMTP_PORT`, `SMTP_EMAIL`, `SMTP_APP_PASSWORD`, and `FRONTEND_URL`. Users must verify their address and opt in through Alerts or Privacy before receiving digests/reminder emails. Verification messages use the durable outbox; password recovery retains its existing direct background delivery. Verification requests are throttled and expired verification mail is not sent.

A digest is queued once per UTC day when there are matches from the previous 24 hours. Incomplete reminders due within 24 hours or overdue by less than seven days are queued once. SMTP failures retry after 15 minutes, up to five attempts; administrators may requeue failed messages. Opt-out cancels pending digest/reminder delivery when next processed. SMTP delivery is at-least-once: a crash after provider acceptance but before database commit can duplicate a message. Tests mock email delivery; no real emails were sent.

## Provider sign-in setup

Register an OAuth application with each provider and set these server environment variables:

```text
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
PUBLIC_BASE_URL=http://localhost:5173
FRONTEND_URL=http://localhost:5173
```

Register these exact callbacks (replace the origin for production):

```text
http://localhost:5173/api/auth/oauth/google/callback
http://localhost:5173/api/auth/oauth/github/callback
```

`PUBLIC_BASE_URL` is the same-site public origin serving the frontend and `/api` proxy. Buttons remain disabled with a clear **Not set up** label until credentials exist. Availability checks time out with retry, and unavailable buttons no longer show a spinning wait cursor. Existing email/password login remains usable.

Provider tokens are exchanged on the backend and are not persisted. Google requires verified email; GitHub requires a verified primary email. For an existing account, sign in first and link the provider in Privacy. Linked providers offer reauthentication. Real provider registration and live authorization require owner configuration and have not been tested here.

References: [Google OpenID Connect](https://developers.google.com/identity/openid-connect/openid-connect), [GitHub OAuth authorization](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps).

## Administrator access and privacy

Set `ADMIN_EMAILS` to a comma-separated allowlist of exact account email addresses. Each account must also verify its email; the backend checks both requirements on every admin request. There is no public role-assignment endpoint. Employer evidence is visible to signed-in users, so exclude private information.

Account deletion closes owned local browser sessions and deletes personal workspace records, uploaded resumes, sessions and linked identities. Moderation reports are retained with the user reference removed; their original text may still contain information the reporter supplied. Platform run logs and database backups follow the host's retention policy.

## Validation

```powershell
.\venv\Scripts\python.exe -m unittest test_platform test_features test_search_history -v
cd frontend
npm run build
```

Eight checks cover account/reset/session lifecycle, profile/tracker isolation, resume lifecycle/coaching/explanations, practice answers, reminders, application details, reporting/admin access, export/deletion, verification and mail retries/opt-out, OAuth state/linking, conservative job identity, preserved requisition IDs, duplicate saves, saved-search CRUD/export, timeline isolation/no-op suppression and backdated pagination. Tests use disposable accounts on configured PostgreSQL and clean up their records. External feed/provider/SMTP/model calls inside integration tests are mocked. Real offline FAISS retrieval was verified separately.

Desktop browser walkthroughs verified sign-in, application board/details, job comparison, resume library/coaching and tools navigation. The new walkthrough verified that a saved Python/Remote search restores filters and returns real dataset matches, and that timeline events appear in chronological order. Temporary preview accounts are removed after testing. Mobile layouts use responsive CSS, but a complete mobile-device pass remains outstanding. No external job application was submitted.

## Before public deployment

Use HTTPS, `COOKIE_SECURE=true`, exact trusted `CORS_ORIGINS` and an explicit `FRONTEND_URL`. Serve the build with SPA fallback and reverse-proxy `/api` on the same site. `vite preview` does not include the development proxy; `VITE_API_URL` optionally supplies a same-site API origin at build time.

Mutations require `X-CareerNova-Client: web`, supplied by the frontend, alongside SameSite cookies and explicit CORS origins. Authentication has a per-process/IP throttle; use a shared gateway limiter for multiple instances. Resume files live in PostgreSQL with account ownership checks and byte/page/decompression limits. Configure encrypted backups and a suitable retention policy for personal data. The worker removes expired sessions/reset tokens/authorization flows periodically.

Nova remains a local single-process assistant with in-memory session ownership and backend-machine browser windows. It is not an isolated hosted browser service. Before exposing automation to untrusted public accounts, use dedicated sandboxed browser workers with destination/redirect egress controls and resource limits. No public deployment, live OAuth approval or real SMTP delivery was performed during implementation.

## Nova website chatbot

Use **Ask Nova** at the bottom-right of any page to ask website questions. The panel provides answers from reviewed CareerNova help, suggested follow-up questions and optional links to the relevant pages. It does not redirect automatically. Short references such as "Where do I find it?" retain the last help topic. New chat clears the conversation, and switching accounts resets it.

`GET /api/chat/help` offers starter topics and warms the local semantic index. `POST /api/chat/message` accepts a question (up to 2,000 characters) and an optional reviewed topic ID. Public visitors can ask how the website works; opening protected feature links still requires login. The endpoint reads no private profile/application records and performs no account mutations.

Semantic retrieval uses the existing `all-MiniLM-L6-v2` embedding model shared with FAISS, with reviewed help answers and internal page links. No external API key is required and chat questions are not sent to an external AI service. Model initialization uses local cached weights only and runs lazily in a background thread. When weights are absent, still loading or unavailable, reviewed keyword search remains usable. Set `CHATBOT_SEMANTIC_ENABLED=false` to keep keyword-only help. This is a retrieval-based website assistant, not an open-ended generative model; unknown questions get a clarification rather than an invented answer.

Messages stay in React memory for the current page/tab, capped at 40 messages. No conversation is written to the account database or browser storage. The backend uses question text transiently to retrieve an answer. Avoid entering passwords or other secrets. The endpoint has a per-process/IP throttle of 30 questions per minute, the standard mutation protection header, input validation and no-store response headers. Use a shared gateway limiter for multi-instance public hosting.

The chat interface includes keyboard Enter/Shift+Enter handling, Escape to close, clear-chat controls, waiting/error/retry states, light/dark styles, mobile layout and reduced-motion support. Update `chatbot_knowledge.py` when feature behavior changes.

Run the expanded regression suite:

```powershell
.\venv\Scripts\python.exe -m unittest test_platform test_features test_search_history test_chatbot -v
```

Chat checks cover feature relevance, follow-up context, unknown questions, semantic paraphrases, safe internal sources, provider availability without exposing credentials, public API validation and throttling. Real local-model retrieval and shared-model FAISS search are checked separately, along with desktop/mobile browser behavior.


### Application memory and consistency

In the application assistant, check **Remember this confirmed answer** before confirming an answer to save it privately for the exact question wording, control type and options. Remembered answers are suggestions and always require confirmation; the candidate profile is not changed. Open **Application memory & consistency** to show or forget answers, select a saved resume and check sources again. Conflicting source values pause automatic profile filling for the affected field. Resume comparison currently checks one distinct extracted email address only, not qualifications or employment dates. Review lists the source of entered answers. Memory is included in privacy export and removed with account deletion.

Verification: `python -m unittest test_application_memory test_application_assistant -v`, and `npm run build` in `frontend`. Employer forms and browser microphone permissions still require live verification.


### Resume drafting and application readiness

The resume library includes a job-specific draft builder. Choose an owned resume and paste a job description, or use **Prepare resume for this job** in discovery. This initial implementation is local keyword-based tailoring, not a generative model: it reorders contiguous bullet groups, highlights supported skills, retains source facts and lists missing skills separately. Review/edit the text and confirm accuracy before saving a new DOCX library version. Originals remain unchanged. The DOCX uses a simple single-column layout; original PDF/design formatting is not retained.

Candidate Profile shows contact, skills, education, experience and saved-resume preparation steps. This checklist is a preparation aid, not an application eligibility assessment.

The application assistant shows filled, unanswered, failed, skipped and manual fields. **Review / retry** revisits an answer. **Rescan current form & recover** reads current text values from the same employer browser after manual edits or navigation. It does not replay old values into a different form or recover a closed browser/backend session.

Checks: `python -m unittest test_resume_tailoring test_application_assistant test_application_memory -v`; `npm run build` in `frontend`.


### Guided interview rehearsal

Open Interview Studio, select a saved resume and enter a target role. An optional job description targets recognized skill questions. The new guided flow asks one question at a time with optional spoken questions and editable browser dictation. Save each answer, explicitly skip questions, save/pause, revisit answers, and resume private sessions. Finish after all questions are answered or skipped to create an immutable feedback report, download it as JSON, or start another attempt. The classic interview worksheet remains available below the guided flow.

Questions use local role/resume templates. Reports explain detected examples, personal actions, outcomes/validation, reflection and missing question concepts. Where cached all-MiniLM-L6-v2 weights exist, the shared local model adds approximate question/answer topic overlap. No model weights are downloaded by this feature. Set `INTERVIEW_SEMANTIC_ENABLED=false` to use pattern coaching only. This is practice feedback, not a correctness test, psychological assessment, voice-quality assessment or hiring prediction. Browser speech recognition may use the browser provider's speech service; CareerNova stores saved text, not audio. Microphone permissions and speech support depend on the browser.

The `mock_interviews` table is created additively at backend startup. Interviews are scoped to the authenticated user, included in privacy export and deleted with the account; a saved session retains its questions if its source resume is removed. Up to 100 sessions per account.

Checks: `python -m unittest test_mock_interview test_features -v`; frontend `npm run build`.


### Job description decoder and application preparation

Open a job's **Apply with Nova** details to view **Understand the role before applying**. Choose a saved resume and use **Decode description & check preparation**. If a listing has no description, paste the employer's wording into the description editor.

The decoder uses local section/wording rules and quotes supplied text for responsibilities, essential requirements, preferred qualifications and working conditions. Unclassified text remains available for review. It identifies unstated topics and document mentions without assuming that a mentioned document is required. Matching recognized required skills to profile/resume text is evidence of keywords only, not eligibility or an ATS score.

The preparation preview checks saved contact details and the selected owned resume and lists manual steps. It does not fetch employer pages or predict application length. Actual form fields, required uploads, login, CAPTCHA and automation support can only be confirmed in the employer application. Descriptions and results are not persisted by the preview endpoint.

Checks: `python -m unittest test_job_preparation -v`; `npm run build` in `frontend`.


### Mixed technical, behavioral and HR interviews

Use **Interview prep** in workspace navigation. Enter a role and start; a resume is now optional. New sessions explicitly mix technical/role-knowledge questions, behavioral examples and HR motivation/expectation questions. Supported role families have dedicated technical prompts, with general professional-knowledge prompts for other roles. Selected resumes and optional descriptions add skill and resume questions. Completed reports include separate Technical, Behavioral and HR summaries, alongside detailed answer feedback. HR feedback checks role connection and motivation rather than requiring a project-style action/result answer. Existing saved sessions retain their original questions and reports.


### Apply from resume matches

Resume Matching result cards now provide **Apply with AI** alongside **Open job posting**. The assisted action opens the existing profile-autofill and voice-confirmation flow; opening a posting directly does not enable automation in that browser. Supported saved Candidate Profile details are filled first, then missing answers are requested. Employer sign-in and verification remain manual; final submission remains with the user.

The matched saved resume is preselected for application uploads. A file uploaded just for matching is retained in the current React page session and offered at the resume-upload question, without automatically storing it in the resume library. Both `apply_url` and `url` result shapes are supported. Historical records can link to expired employer pages.

Checks: frontend `node --test src/resumeApplication.test.mjs` and `npm run build`; backend `python -m unittest test_application_assistant test_application_memory -v`.


### Detecting employer Application tabs

While waiting for an employer form or login, the application assistant now polls its owned session every three seconds. It rescans the current assisted context, follows a newly opened employer tab, and begins profile autofill when application fields are found. It does not click employer controls or submit forms. Overview/search-only controls remain in the waiting stage. Use **Application is open — Scan & fill saved details** for a manual retry. The ordinary **Name** label (including required markers) now maps to the saved first and last name; employer forms such as the Ashby-style Name, Email, LinkedIn URL and numeric Years of Experience fields have regression coverage.

After a backend reload, close the old assistant session and start **Apply with AI** again; sessions are local process-owned and cannot survive reloads.
