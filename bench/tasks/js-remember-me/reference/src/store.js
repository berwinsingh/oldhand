import { randomBytes } from 'node:crypto';

export const HOUR = 60 * 60 * 1000;
export const THIRTY_DAYS = 30 * 24 * HOUR;

const sessions = new Map();

// A remembered session lives 30 days, a normal one an hour; refresh re-creates the same kind.
export function create(email, remember) {
  const sid = randomBytes(18).toString('base64url');
  sessions.set(sid, { email, remember, expiresAt: Date.now() + (remember ? THIRTY_DAYS : HOUR) });
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
