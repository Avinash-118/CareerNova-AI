# CareerNova deployment

The existing frontend project is `career-nova-ai`, rooted at `frontend`, connected to `Avinash-118/CareerNova-AI`. Its public URL is https://career-nova-ai-one.vercel.app/.

## Services and cost limits

- Vercel serves the built React frontend. Its Hobby plan is for personal, non-commercial use: https://vercel.com/docs/plans/hobby.
- Hugging Face now requires a paid plan to create CPU Docker Spaces. This account shows Docker as Paid, so it is not a zero-cost backend choice: https://huggingface.co/docs/hub/spaces-gpus. The Docker package can instead be used by another compatible container host.
- Neon provides remote PostgreSQL. Select the free plan and monitor storage/compute quotas: https://neon.com/pricing.
- Email uses existing SMTP locally. For hosts that block SMTP ports, optional Brevo HTTPS delivery is supported. It requires a verified sender and API key and has free-tier limits: https://developers.brevo.com/docs/send-a-transactional-email.

Do not select paid hardware, upgrades or persistent-storage plans for a zero-cost deployment. Use free provider subdomains; a custom domain is not required.

## Backend bundle

```powershell
.\venv\Scripts\python.exe build_deployment_bundle.py
```

The generated `.deploy/backend` folder and ZIP contain only backend code, Docker configuration and dependencies. They exclude `.env`, personal resumes, databases, backup files, frontend dependencies and job datasets. Use the folder as the build context for a compatible container host. The included Hugging Face README is a template only; do not create a paid Space when the budget is zero. Render can build the root Dockerfile from GitHub on its Free web-service plan, subject to memory, sleep and network limits: https://render.com/docs/free.

Configure these in the backend's private secret/variable settings:

```text
APP_ENV=production
DATABASE_URL=<Neon PostgreSQL connection URI with SSL enabled>
FRONTEND_URL=https://career-nova-ai-one.vercel.app
PUBLIC_BASE_URL=https://career-nova-ai-one.vercel.app
CORS_ORIGINS=https://career-nova-ai-one.vercel.app
COOKIE_SECURE=true
APPLICATION_ASSISTANT_ENABLED=false
RUN_ALERT_WORKER=false
```

Never put database URLs, SMTP passwords or provider keys in `VITE_*` variables, source control, public files or chat. Existing local accounts/resumes are not automatically migrated. Use the selected cloud database only after checking it is the intended project; never overwrite another project's data.

For HTTPS email, additionally set `EMAIL_PROVIDER=brevo`, `EMAIL_FROM` to a verified sender, and `BREVO_API_KEY` as a secret. Otherwise SMTP requires outbound ports permitted by the chosen host. Registration and sign-in can work without configured email, but recovery/verification delivery cannot.

If `RUN_ALERT_WORKER=true`, the container starts the existing worker after the API is ready. The worker stops if the free container sleeps; therefore alerts are not continuously guaranteed. Enable it only after reviewing the selected cloud database's alert rules and outbox, because queued messages may be sent.

## Dataset and model requirements

Historical job browsing and FAISS resume matching require `jobs_metadata.parquet` and `jobs_faiss.index` on the backend in `JOB_DATA_DIR` (default `/data` in the container). These are not uploaded in the source bundle. Provision authorized job artifacts separately. Without them, the API returns an explicit unavailable response; live job search and the other account tools remain usable.

The sentence-transformer model loads lazily. Website help and interview coaching have non-semantic fallbacks if local model weights are absent. A cold model load can take time. The browser-based application assistant is disabled in cloud mode: its headed browser runs on the server and cannot appear or execute in a visitor's computer. It stays available in local development. A remotely usable application assistant requires a separate browser-extension/local-companion design.

## Frontend routing

Once the backend has a working public HTTPS URL:

```powershell
.\venv\Scripts\python.exe configure_deployment.py --backend https://YOUR-BACKEND.hf.space
```

This writes `frontend/vercel.json` with the API reverse proxy before the SPA fallback. The browser keeps same-origin cookies; leave `VITE_API_URL` unset/empty. Set Vercel `VITE_DEFAULT_JOB_SOURCE=live` when the historical dataset is not installed. Keep Root Directory `frontend`, build command `npm run build`, output directory `dist`.

Test the backend `/api/health` first. Then create a preview deployment, verify sign-up, login, refresh, profile save/reload, deep-link routes, resume uploads and interview history, and only then promote the new version to production. Verify reset email after configuring the email provider. Do not replace a working production deployment with an unconnected frontend.

## Verification

```powershell
.\venv\Scripts\python.exe -m unittest test_deployment test_email_transport test_platform test_mock_interview -v
cd frontend
npm run build
```

Container builds and hosted account flows have now been checked as recorded below. A passing local build alone does not confirm deployment.


## Zero-cost Render alternative

`render.yaml` explicitly selects a Free Docker web service and disables the in-memory semantic model for website help and interview feedback to reduce memory use. Those tools retain their local wording/template fallbacks. Historical FAISS artifacts are still provisioned separately, and the desktop application assistant remains local-only. Sign in to Render, connect the existing GitHub repository, review the blueprint and set the Neon `DATABASE_URL` as a secret. Do not choose a paid instance. Verify memory use and health on the Free instance before promoting the Vercel frontend. Render Free services sleep and block SMTP ports; use a verified HTTPS email provider if email is needed.

A blueprint does not deploy itself until applied in the hosting account. No Render service has been created merely by adding this file.


## Verification completed locally

The Linux Docker image built successfully. A backend-import smoke check under a 512 MB container limit completed with approximately 206 MB peak resident memory, without a database connection, loaded semantic model or job-index artifacts. This is a baseline check, not a full traffic/load test. Fourteen deployment/auth/email/interview tests and the frontend build passed.

Deployment completed on 2026-10-19: frontend https://career-nova-ai-one.vercel.app, backend https://careernova-api.onrender.com, with Neon PostgreSQL. Vercel production was promoted from codex/free-public-deployment. Render tracks that branch; main was not modified. The connection secret was entered by the owner directly in Render. Hosted checks verified registration, email/password login, session persistence after reload, profile save/reload, live job results, saved jobs, and role-only interview startup. The final health endpoint queries PostgreSQL. No test emails were sent.

Cloud limitations: Google/GitHub OAuth is not configured; outgoing email and RUN_ALERT_WORKER remain disabled until a verified HTTPS email provider is configured. Historical FAISS artifacts are not provisioned, semantic feedback models are disabled for memory limits, and the headed application assistant remains local-only. Free Render sleeps when idle. Local accounts and resumes were not migrated. One synthetic deployment-check account remains for verification; it contains no real candidate information.

Additional verification: an isolated Linux container and fresh PostgreSQL 18 passed registration and profile round-trip checks under a 512 MB API memory limit. After the hosted driver fix, four deployment tests and the frontend build passed. A later combined local suite stalled during database integration startup and was stopped; it is not counted as a passing rerun.

## Free public job feeds (2026-10-23)

Default discovery now uses Himalayas (up to five cursor pages, 100 listings) and Arbeitnow (one provider page; currently 300 listings). No API keys or paid services are required. This is a bounded sample, not a complete job market index. Existing search, alerts and live resume matching consume the normalized feed; local FAISS matching remains available when its artifacts are present.

Each provider is cached for 24 hours per Python process; the combined cache lasts 15 minutes. Container restarts clear these in-memory caches. Provider failures are reported independently and do not silently retain old results indefinitely. Himalayas expiry dates are checked on cached reads, applicationLink values are preserved, and source backlinks appear in job cards and the footer. Timezone restrictions are retained in job metadata; candidates must check the original posting for all eligibility requirements. Listings can close before their advertised expiry. Arbeitnow does not supply an expiry date in this integration.

Remotive is excluded from default discovery because its public-feed terms disallow signup-gated access. Existing saved records are preserved. USAJOBS is not enabled because it requires separate registration for a free API key. No paid plan or credential is needed for the two default providers. No resume or candidate data is sent to them. Cloud resume matching continues to use its existing keyword fallback when FAISS artifacts are absent.

Verification: six targeted unit tests passed, frontend production build passed, and a live bounded fetch returned 400 jobs (100 Himalayas, 300 Arbeitnow). This records local implementation checks, not production deployment.
