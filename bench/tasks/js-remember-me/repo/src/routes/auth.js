import { readFileSync } from 'node:fs';
import { cookies, send } from '../app.js';
import { sessionCookie } from '../session.js';
import * as store from '../store.js';

const users = JSON.parse(readFileSync(new URL('../../data/users.json', import.meta.url), 'utf8'));

export function login(req, res, body) {
  const user = users.find((u) => u.email === body.email && u.password === body.password);
  if (!user) return send(res, 401, { error: 'wrong email or password' });
  const remember = Boolean(body.remember);
  const sid = store.create(user.email, remember ? store.THIRTY_DAYS : store.HOUR);
  return send(res, 200, { email: user.email }, { 'set-cookie': sessionCookie(sid, remember) });
}

export function refresh(req, res) {
  const old = cookies(req).sid;
  const session = store.get(old);
  if (!session) return send(res, 401, { error: 'not signed in' });
  store.drop(old);
  const sid = store.create(session.email, store.HOUR);
  return send(res, 200, { email: session.email }, { 'set-cookie': `sid=${sid}; HttpOnly; Path=/; SameSite=Lax` });
}

export function logout(req, res) {
  store.drop(cookies(req).sid);
  return send(res, 200, { ok: true }, { 'set-cookie': 'sid=; HttpOnly; Path=/; SameSite=Lax; Max-Age=0' });
}

export function me(req, res) {
  const session = store.get(cookies(req).sid);
  if (!session) return send(res, 401, { error: 'not signed in' });
  return send(res, 200, { email: session.email, expiresAt: session.expiresAt });
}
