import { randomBytes } from 'node:crypto';

export const HOUR = 60 * 60 * 1000;
export const THIRTY_DAYS = 30 * 24 * HOUR;

const sessions = new Map();

export function create(email, ttl) {
  const sid = randomBytes(18).toString('base64url');
  sessions.set(sid, { email, expiresAt: Date.now() + ttl, remember: ttl > HOUR });
  return sid;
}

export function get(sid) {
  const s = sid && sessions.get(sid);
  if (!s) return null;
  if (s.expiresAt <= Date.now()) {
    sessions.delete(sid);
    return null;
  }
  return s;
}

export function drop(sid) {
  sessions.delete(sid);
}
