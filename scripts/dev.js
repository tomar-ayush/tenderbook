// Local run without the Vercel CLI: serves frontend/ and the api/ functions on http://127.0.0.1:3000.
// Reads .env (DATABASE_URL and the contract fields) from this folder:  npm run dev
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { existsSync, readFileSync } from 'node:fs';
import { extname, join, normalize } from 'node:path';

if (existsSync('.env')) for (const line of readFileSync('.env', 'utf8').split('\n')) {
  const m = /^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)\s*$/.exec(line);
  if (m && m[2] && !(m[1] in process.env)) process.env[m[1]] = m[2].replace(/^["']|["']$/g, '');
}
const TYPES = { '.html': 'text/html; charset=utf-8', '.json': 'application/json', '.js': 'text/javascript' };
const port = Number(process.env.PORT || 3000);

createServer(async (req, res) => {
  const path = new URL(req.url, 'http://x').pathname;
  try {
    if (path.startsWith('/api/')) {
      const name = path.slice(5).replace(/[^a-z]/g, '');
      if (!existsSync(`api/${name}.js`)) { res.statusCode = 404; return res.end('{"error":"not found"}'); }
      return (await import(`../api/${name}.js`)).default(req, res);
    }
    const file = join('frontend', normalize(path === '/' ? '/index.html' : path).replace(/^(\.\.[/\\])+/, ''));
    res.setHeader('Content-Type', TYPES[extname(file)] || 'application/octet-stream');
    res.end(await readFile(file));
  } catch {
    res.statusCode = 404; res.end('not found');
  }
}).listen(port, '127.0.0.1', () => console.log(`http://127.0.0.1:${port}`));
