# Tenderbook

Bid history, buyers and competitors of every seller on GeM, read live from the pipeline's PostgreSQL.

```
frontend/   the page (static): index.html, india.json (map, @svg-maps/india, CC BY 4.0)
api/        the backend: Vercel runs each file as a function; it reads Postgres with a read-only login
lib/db.js   the queries the functions share
db/create-web-role.sh   run once on the VM: makes that read-only login and prints its DATABASE_URL
scripts/    dev.js (local run), build_frontend.py (rebuilds frontend/index.html from the design page)
```

Browser -> Vercel (page + `/api/*`) -> Postgres on the VM, port 5433, TLS, a login that can only `SELECT` six tables.
Vercel's CDN keeps each API answer for 10 minutes, so most visits never reach the database.

## Deploy (once)

**1. On the VM** (copy this one file there, or clone the repo):

```bash
bash db/create-web-role.sh
```

It creates the `tenderbook_web` login (read-only, 15 s statement limit, at most 20 connections), checks it can read
and cannot write, and prints a `DATABASE_URL`. Run it again any time to get a new password.

**2. On Vercel:** Add New Project, import this GitHub repo, keep every build setting as it is, and add the
environment variables from `.env.example`:

| Variable | Value |
|---|---|
| `DATABASE_URL` | the URL the script printed |
| `CONTRACT_TOTAL_FIELD`, `CONTRACT_STATUS_FIELD` | the two contract-list labels (from the pipeline owner); without them a won bid shows its offered price |
| `PG_CA_CERT` | optional, the server's certificate to verify it |

Deploy. Check `https://<project>.vercel.app/api/health` says `{"ok":true}`.

## After that

`git push` to `main` deploys. Nothing to run on the VM.

## Run on your laptop

```bash
npm install
cp .env.example .env      # fill in DATABASE_URL (and the contract fields)
npm run dev               # http://127.0.0.1:3000
```

## Changing the design

The page is generated from the design file so the design itself stays untouched:
`python3 scripts/build_frontend.py path/to/company.src.html`, then commit `frontend/index.html`.
