import { respond, search } from '../../../lib/db';

// GET /api/companies?q=raj&sort=bids&page=0  ->  { companies: [...50], total, page, per_page, sort }
// sort: bids, won, value, rate (companies with at least 10 bids), name
export const GET = respond(async ({ q, sort, page }) => [200, await search(q, sort, page)]);
