import { createServer } from 'node:http';
import { login, logout, me, refresh } from './routes/auth.js';

const routes = { 'POST /login': login, 'POST /refresh': refresh, 'POST /logout': logout, 'GET /me': me };

export function send(res, status, body, headers = {}) {
  res.writeHead(status, { 'content-type': 'application/json', ...headers });
  res.end(JSON.stringify(body));
}

async function readJson(req) {
  let raw = '';
  for await (const chunk of req) raw += chunk;
  try {
    return raw ? JSON.parse(raw) : {};
  } catch {
    return null;
  }
}

export function cookies(req) {
  const out = {};
  for (const part of (req.headers.cookie || '').split(';')) {
    const [k, ...v] = part.trim().split('=');
    if (k) out[k] = v.join('=');
  }
  return out;
}

export function makeServer() {
  return createServer(async (req, res) => {
    const handler = routes[`${req.method} ${new URL(req.url, 'http://x').pathname}`];
    if (!handler) return send(res, 404, { error: 'not found' });
    const body = await readJson(req);
    if (body === null) return send(res, 400, { error: 'bad json' });
    return handler(req, res, body);
  });
}
