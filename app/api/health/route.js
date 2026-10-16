import { query, respond } from '../../../lib/db';

// GET /api/health  ->  { ok: true } when the database answers
export const GET = respond(async () => {
  await query('SELECT 1');
  return [200, { ok: true }];
}, false);
