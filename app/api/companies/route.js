import { respond, search } from '../../../lib/db';

// GET /api/companies?q=raj  ->  { companies: [...] }   up to 20 matches, or the most active companies when q is empty
export const GET = respond(async ({ q }) => [200, { companies: await search(q) }]);
