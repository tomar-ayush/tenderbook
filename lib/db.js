// Reads the company tables from Postgres for the app/api routes. A warm function keeps its pool between requests.
// DATABASE_URL must be the read-only login made by db/create-web-role.sh, never the owner.
import pg from 'pg';

pg.types.setTypeParser(20, v => Number(v)); // bigint ids (company_id, tender_id) as numbers; they stay far below 2^53

const url = new URL(process.env.DATABASE_URL || 'postgresql://localhost/none');
url.searchParams.delete('sslmode'); // TLS is set below; pg would otherwise treat "require" as "verify the certificate"
const ssl = process.env.PG_CA_CERT ? { ca: process.env.PG_CA_CERT } // verify the server's certificate
  : process.env.PG_SSL === 'off' ? false : { rejectUnauthorized: false }; // encrypted; the server's own certificate is self-signed

const pool = new pg.Pool({ connectionString: url.toString(), ssl, max: 3, idleTimeoutMillis: 10_000, connectionTimeoutMillis: 8_000 });

export async function query(sql, params = []) {
  return (await pool.query(sql, params)).rows;
}

const MAX_TENDERS = Number(process.env.MAX_TENDERS || 3000); // a company's most recent bids sent to the page
const MAX_RIVALS = Number(process.env.MAX_RIVALS || 300); // competitors listed per period, most met first
const IST = col => `to_char(${col} AT TIME ZONE 'Asia/Kolkata', 'YYYY-MM-DD"T"HH24:MI:SS"+05:30"')`;
const END = 'coalesce(t.bid_end_at, t.ra_end_at, t.bid_start_at)';

export async function search(q) {
  q = String(q || '').trim().slice(0, 80);
  const typed = q.length >= 2;
  const like = '%' + q.replace(/[\\%_]/g, c => '\\' + c) + '%';
  return query(`
    SELECT c.company_id, c.display_name, s.total_bids, s.awarded_bids, s.awarded_value::float AS awarded_value, s.win_rate::float AS win_rate
    FROM company c JOIN company_summary s USING (company_id)
    ${typed ? 'WHERE c.display_name ILIKE $1' : ''}
    ORDER BY s.total_bids DESC, c.company_id
    LIMIT 20`, typed ? [like] : []);
}

async function tenderIds(companyId) {
  const rows = await query(`
    SELECT p.tender_id FROM participation p JOIN tender t USING (tender_id)
    WHERE p.company_id = $1 ORDER BY ${END} DESC NULLS LAST LIMIT $2`, [companyId, MAX_TENDERS]);
  return rows.map(r => r.tender_id);
}

// a bid's contracts are found by its bid or RA number; the contract's seller is the bid's winner (outcome_source 1).
// The two field names are the labels of the stored contract list; they are settings so they are not in this public code.
function contractsSql() {
  const total = process.env.CONTRACT_TOTAL_FIELD, status = process.env.CONTRACT_STATUS_FIELD;
  if (!total || !status) return null;
  return `
    SELECT t.tender_id,
           sum(replace(substring(coalesce(c.list_fields->>$3, c.doc_fields->>'item_total') FROM '[0-9,]+[.]?[0-9]*'), ',', '')::numeric)::float AS total
    FROM tender t
    JOIN stg_contract c ON c.bid_number IN (t.bid_number, t.ra_number)
    JOIN participation p ON p.tender_id = t.tender_id AND p.company_id = $1 AND p.outcome = 1 AND p.outcome_source = 1
    WHERE t.tender_id = ANY($2::bigint[]) AND coalesce(c.list_fields->>$4, '') NOT ILIKE '%cancel%'
    GROUP BY t.tender_id`;
}

export async function company(companyId) {
  const [found] = await query('SELECT company_id, display_name, status FROM company WHERE company_id = $1', [companyId]);
  if (!found) return null;
  const ids = await tenderIds(companyId);
  const contractSql = contractsSql();
  const [tenders, part, authorities, rivalRows, contractRows] = await Promise.all([
    query(`SELECT tender_id, bid_number, ra_number, buyer_org_id, category, quantity::float AS quantity, awarded, state,
                  ${IST(END)} AS bid_end_at
           FROM tender t WHERE tender_id = ANY($1::bigint[])`, [ids]),
    query(`SELECT tender_id, company_id, raw_name, ${IST('participated_at')} AS participated_at, offered_make, offered_model,
                  tech_status, mse_mii_status, offered_price::float AS offered_price, price_rank, outcome, outcome_source
           FROM participation WHERE company_id = $1 AND tender_id = ANY($2::bigint[])`, [companyId, ids]),
    query(`SELECT o.buyer_org_id, o.organisation, o.ministry, o.department, o.office,
                  mode() WITHIN GROUP (ORDER BY t.state) FILTER (WHERE t.state IS NOT NULL) AS state
           FROM buyer_org o JOIN tender t USING (buyer_org_id)
           WHERE t.tender_id = ANY($1::bigint[]) GROUP BY o.buyer_org_id`, [ids]),
    // what the page's rivals() used to count in the browser, done here per period: a busy seller shares bids with
    // thousands of companies, far too many rows to send
    query(`
      WITH mine AS (
        SELECT p.tender_id, p.outcome, p.price_rank, ${END} AS end_at
        FROM participation p JOIN tender t USING (tender_id)
        WHERE p.company_id = $1 AND p.tender_id = ANY($2::bigint[])
      ), counted AS (
        SELECT per.period, o.company_id AS id, count(*)::int AS shared,
               (count(*) FILTER (WHERE m.outcome = 1))::int AS our_wins,
               (count(*) FILTER (WHERE o.outcome = 1))::int AS their_wins,
               (count(*) FILTER (WHERE m.price_rank < o.price_rank))::int AS beat,
               (count(*) FILTER (WHERE m.price_rank > o.price_rank))::int AS lost_to,
               ${IST('max(m.end_at)')} AS last
        FROM mine m
        JOIN participation o ON o.tender_id = m.tender_id AND o.company_id <> $1
        CROSS JOIN (VALUES ('12m', 365), ('24m', 730), ('all', 99999)) AS per(period, days)
        WHERE m.end_at >= now() - per.days * interval '1 day'
        GROUP BY per.period, o.company_id
      )
      SELECT * FROM (SELECT *, row_number() OVER (PARTITION BY period ORDER BY shared DESC, their_wins DESC, id) AS n FROM counted) x
      WHERE n <= $3`, [companyId, ids, MAX_RIVALS]),
    contractSql ? query(contractSql, [companyId, ids, process.env.CONTRACT_TOTAL_FIELD, process.env.CONTRACT_STATUS_FIELD]) : [],
  ]);
  const rivals = { '12m': [], '24m': [], all: [] };
  for (const { period, n, ...r } of rivalRows) rivals[period].push(r);
  const others = [...new Set(rivalRows.map(r => r.id))];
  const companies = others.length ? await query('SELECT company_id, display_name, status FROM company WHERE company_id = ANY($1::bigint[])', [others]) : [];
  return {
    company: found, tenders, part, authorities, rivals, companies,
    contracts: contractRows.filter(r => r.total != null).map(r => ({ tender_id: r.tender_id, company_id: companyId, total: r.total })),
    limited: ids.length === MAX_TENDERS,
  };
}

export async function rival(companyId, rivalId) {
  const ids = await tenderIds(companyId);
  return {
    part: await query(`SELECT tender_id, company_id, raw_name, ${IST('participated_at')} AS participated_at, offered_make, offered_model,
                              tech_status, mse_mii_status, offered_price::float AS offered_price, price_rank, outcome, outcome_source
                       FROM participation WHERE company_id = $1 AND tender_id = ANY($2::bigint[])`, [rivalId, ids]),
  };
}

// wraps a route: JSON out, CDN caching for good answers, errors that never show SQL
export function respond(fn, cache = true) {
  return async request => {
    const args = Object.fromEntries(new URL(request.url).searchParams);
    try {
      const [status, body] = await fn(args);
      return Response.json(body, { status, headers: { 'Cache-Control': cache && status === 200
        ? 'public, max-age=60, s-maxage=600, stale-while-revalidate=3600' : 'no-store' } });
    } catch (e) {
      console.error(request.url, e);
      return Response.json({ error: 'server error' }, { status: 500, headers: { 'Cache-Control': 'no-store' } });
    }
  };
}

export const isId = v => /^[0-9]{1,12}$/.test(String(v || ''));
