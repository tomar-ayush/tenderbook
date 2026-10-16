// GET /api/rival?id=41827&rival=50210  ->  { part: [...] }   that competitor's rows on the bids the two shared
import { handler, isId, rival } from '../lib/db.js';

export default handler(async ({ id, rival: other }) => {
  if (!isId(id) || !isId(other)) return [400, { error: 'id and rival must be numbers' }];
  return [200, await rival(Number(id), Number(other))];
});
