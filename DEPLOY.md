# Deploying the demo (free) on Render

The app is deploy-ready: `render.yaml`, `Procfile`, `gunicorn`, a SQLite
fallback, and auto-seeding (`AUTO_SEED=1`) are all configured. On first boot
Render will install dependencies, start gunicorn, and seed the demo data
automatically.

## One-time: push the code to GitHub

1. Create a free account at https://github.com and click **New repository**.
   - Name: `spit-finance-portal`  ·  Visibility: **Public**  ·  do *not* add a README.
2. Create a **Personal Access Token** (used as your git password):
   - https://github.com/settings/tokens → **Generate new token (classic)**
   - Scope: tick **repo** · Generate · copy the token (starts with `ghp_…`).
3. From the project folder, push (replace `USERNAME`):
   ```bash
   git remote add origin https://github.com/USERNAME/spit-finance-portal.git
   git branch -M main
   git push -u origin main
   ```
   When prompted: username = your GitHub username, password = the token.

## Deploy on Render

1. Sign up at https://render.com (use "Sign in with GitHub").
2. **New +** → **Blueprint** → pick your `spit-finance-portal` repo.
   Render reads `render.yaml` and configures everything automatically.
3. Click **Apply**. First build takes ~3–5 minutes.
4. You get a public URL like `https://spit-finance-portal.onrender.com`.

> Free tier note: the service sleeps after ~15 min idle; the first request
> then takes ~30s to wake. The SQLite demo data resets to its seeded state on
> each cold start — which is ideal for a clean demo.

## Demo credentials

| Role | Email | Password |
|------|-------|----------|
| Committee | committee@spit.ac.in | Committee@SPIT26 |
| Finance Secretary | finance@spit.ac.in | Finance@SPIT26 |
| Associate Dean | assocdean@spit.ac.in | AssocDean@SPIT26 |
| Dean | dean@spit.ac.in | Dean@SPIT26 |
