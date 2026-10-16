// GET /api/companies?q=raj  ->  { companies: [...] }   up to 20 matches, or the most active companies when q is empty
import { handler, search } from '../lib/db.js';

export default handler(async ({ q }) => [200, { companies: await search(q) }]);
