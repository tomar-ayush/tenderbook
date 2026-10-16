# Tenderbook

Bid history, buyers and competitors of every seller on GeM, read live from the pipeline's PostgreSQL.
A Next.js app: the page and its API in one project, so Vercel deploys both from a `git push`.

```
app/page.js, app/shell.js, app/design.css, public/app.js   the page (generated from the design; see below)
app/api/*/route.js     the API: health, companies (search), company (profile), rival (head to head)
lib/db.js              the queries, through a read-only Postgres login
db/create-web-role.sh  run once on the VM: makes that login and prints its DATABASE_URL
public/india.json      the map (@svg-maps/india, CC BY 4.0)
```

Browser -> Vercel (page + `/api/*`) -> Postgres on the VM, port 5433, TLS, a login that can only `SELECT` six tables.
Vercel's CDN keeps each API answer for 10 minutes, so most visits never reach the database.

## Deploy (once)

**1. On the VM:**

```bash
git clone https://github.com/tomar-ayush/tenderbook && bash tenderbook/db/create-web-role.sh
```

It creates the `tenderbook_web` login (read-only, 15 s statement limit, at most 20 connections), checks it can read
and cannot write, and prints a `DATABASE_URL`. Run it again any time to get a new password.

**2. On Vercel:** import this repo. Framework: Next.js (detected). **Root Directory: leave empty** (the repo root).
Add the environment variables from `.env.example`:

| Variable | Value |
|---|---|
| `DATABASE_URL` | the URL the script printed |
| `CONTRACT_TOTAL_FIELD`, `CONTRACT_STATUS_FIELD` | the two contract-list labels (from the pipeline owner); without them a won bid shows its offered price |
| `PG_CA_CERT` | optional, the server's certificate to verify it |

Deploy, then check `https://<project>.vercel.app/api/health` says `{"ok":true}`.

After that, `git push` to `main` deploys.

## Run on your laptop

```bash
npm install
cp .env.example .env      # fill in DATABASE_URL (and the contract fields)
npm run dev               # http://localhost:3000
```

## Changing the design

The page is generated from the design file, so the design itself stays untouched:
`python3 scripts/build_frontend.py path/to/company.src.html` rewrites `app/shell.js`, `app/design.css` and
`public/app.js`; commit them.
