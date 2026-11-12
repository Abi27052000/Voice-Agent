# Deploy the demo for free (Google Cloud Run + Firebase Hosting)

Hosts the backend on **Cloud Run** (scales to zero) and the frontend on **Firebase Hosting**, inside their free tiers. Recruiter traffic should cost **$0**; verify the current free-tier limits on Google's pricing pages, since they change and some apply only to US regions.

| Part | Service | Free-tier notes |
|---|---|---|
| API + Vapi webhook | Cloud Run, `us-central1` | `min-instances=0` (no idle cost), `max-instances=1` (caps spend, keeps one SQLite DB) |
| Website | Firebase Hosting | Static files |
| Database | SQLite in the container's `/tmp` | Re-seeded with fictional data on every fresh start, so the demo **resets itself** after idle periods |

> **The real cost is Vapi credit, not hosting.** Each demo call spends a few cents. Without a payment method on Vapi, calls simply stop when credit runs out. Do step 7 (lock the public key) before sharing the link.

Commands below use `PROJECT_ID` as a placeholder; replace it with your project's ID. Run them from the repo root unless noted. On Windows PowerShell, put each command on one line (remove the `\` line breaks).

## 1. Project, billing, and APIs

```bash
gcloud projects create PROJECT_ID            # or reuse an existing project
gcloud config set project PROJECT_ID
gcloud billing accounts list                 # the account holding your credits
gcloud billing projects link PROJECT_ID --billing-account=BILLING_ACCOUNT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
```

Add a **budget alert** (Billing → Budgets & alerts) for this project, e.g. $1, so any unexpected spend is flagged immediately.

## 2. Firebase project (to get the site URL)

```bash
npx firebase-tools login
npx firebase-tools projects:addfirebase PROJECT_ID
```

Your site will be `https://PROJECT_ID.web.app` (also `https://PROJECT_ID.firebaseapp.com`).

## 3. Cloud Run environment file

```bash
cd backend
uv run python -m scripts.cloud_run_env --frontend https://PROJECT_ID.web.app --frontend https://PROJECT_ID.firebaseapp.com
```

This writes `backend/data/deploy/cloud-run.env.yaml` (gitignored; it contains your Vapi keys) with the keys, Vapi resource IDs, CORS origins, `PUBLIC_DEMO=true`, and `SEED_DEMO_DATA=true`.

## 4. Deploy the backend

```bash
# still in backend/
gcloud run deploy ridgeway-api \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --env-vars-file data/deploy/cloud-run.env.yaml \
  --min-instances 0 --max-instances 1 \
  --memory 512Mi --cpu 1
```

Cloud Build builds the `Dockerfile`. `.gcloudignore` keeps `.env`, `data/`, and `vapi/ids.json` out of the upload. Copy the **Service URL** from the output (`https://ridgeway-api-…run.app`), then check it:

```bash
curl https://YOUR_SERVICE_URL/api/health
```

## 5. Point Vapi at Cloud Run (replaces ngrok)

In `backend/.env`, set `PUBLIC_BASE_URL=https://YOUR_SERVICE_URL` (no trailing path), then:

```bash
uv run python -m scripts.sync_vapi --check   # shows "Tools will call: https://YOUR_SERVICE_URL/api/vapi/webhook"
uv run python -m scripts.sync_vapi
```

Every tool, the webhook credential, and every assistant now point at Cloud Run, and **ngrok is no longer needed**.

> Local development afterwards: Vapi's tool calls now go to Cloud Run, not your laptop. To develop locally again, set `PUBLIC_BASE_URL` back to your ngrok URL and re-run `scripts.sync_vapi`, and re-run it with the Cloud Run URL when you're done.

## 6. Deploy the frontend

```bash
cd ../frontend
cp .env.production.example .env.production   # set VITE_API_URL=https://YOUR_SERVICE_URL/api
npm run build
npx firebase-tools deploy --only hosting --project PROJECT_ID
```

## 7. Lock down the Vapi public key

Vapi dashboard → **API Keys** → Public Key → **Origins**: allow only `https://PROJECT_ID.web.app`, `https://PROJECT_ID.firebaseapp.com`, and `http://localhost:5173` (for local development). Without this, any website could start calls on your credit.

## 8. Smoke test

Open `https://PROJECT_ID.web.app`:

- [ ] The blue "public demo with fictional data" banner shows
- [ ] **Dashboard** shows seeded appointments; **Win-back** shows 12 past customers
- [ ] **Front desk:** a short booking call books a window (the first call after idle may take a few extra seconds while Cloud Run starts)
- [ ] The call appears on the Dashboard with a summary within a minute

## Notes

- **Data resets** whenever Cloud Run starts a fresh instance (after idle time or a redeploy). That's intended for a demo; nothing is stored long-term.
- **Post-call outcome polling:** Cloud Run limits CPU between requests, so the background re-check for late-arriving call outcomes may be delayed. In testing, outcomes almost always arrived with the end-of-call report.
- **Redeploying** after code changes: repeat step 4 (and step 6 for frontend changes). Re-run step 3 only if keys, IDs, or URLs changed.
- **Taking it down:** `gcloud run services delete ridgeway-api --region us-central1` and `npx firebase-tools hosting:disable --project PROJECT_ID`, or delete the whole project.
