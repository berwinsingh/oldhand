import { THIRTY_DAYS } from './store.js';

// The Set-Cookie value for a session id.
export function sessionCookie(sid, remember) {
  const parts = [`sid=${sid}`, 'HttpOnly', 'Path=/', 'SameSite=Lax'];
  if (remember) parts.push(`Max-Age=${THIRTY_DAYS / 1000}`);
  return parts.join('; ');
}
