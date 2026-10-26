import { readFileSync } from 'node:fs';
import { createServer } from 'node:http';

export function loadItems(path = new URL('./data/items.json', import.meta.url)) {
  return JSON.parse(readFileSync(path, 'utf8'));
}

function send(res, status, body) {
  res.writeHead(status, { 'content-type': 'application/json' });
  res.end(JSON.stringify(body));
}

export function makeServer(items = loadItems()) {
  return createServer((req, res) => {
    const url = new URL(req.url, 'http://localhost');
    if (req.method !== 'GET') return send(res, 405, { error: 'method not allowed' });

    if (url.pathname === '/items') {
      const wanted = url.searchParams.getAll('tag').map((t) => t.toLowerCase());
      const found = items.filter((it) => {
        const have = new Set(it.tags.map((t) => t.toLowerCase()));
        return wanted.every((t) => have.has(t));
      });
      return send(res, 200, found);
    }
    const m = /^\/items\/(\d+)$/.exec(url.pathname);
    if (m) {
      const item = items.find((it) => it.id === Number(m[1]));
      return item ? send(res, 200, item) : send(res, 404, { error: 'not found' });
    }
    return send(res, 404, { error: 'not found' });
  });
}
