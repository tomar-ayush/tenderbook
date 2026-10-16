import { isId, respond, rival } from '../../../lib/db';

// GET /api/rival?id=41827&rival=50210  ->  { part: [...] }   that competitor's rows on the bids the two shared
export const GET = respond(async ({ id, rival: other }) => {
  if (!isId(id) || !isId(other)) return [400, { error: 'id and rival must be numbers' }];
  return [200, await rival(Number(id), Number(other))];
});
