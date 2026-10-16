// GET /api/health  ->  { ok: true } when the database answers
import { handler, query } from '../lib/db.js';

export default handler(async () => {
  await query('SELECT 1');
  return [200, { ok: true }];
});
