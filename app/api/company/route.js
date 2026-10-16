import { company, isId, respond } from '../../../lib/db';

// GET /api/company?id=41827  ->  { company, tenders, part, authorities, rivals, companies, contracts, limited }
export const GET = respond(async ({ id }) => {
  if (!isId(id)) return [400, { error: 'id must be a number' }];
  const found = await company(Number(id));
  return found ? [200, found] : [404, { error: 'company not found' }];
});
