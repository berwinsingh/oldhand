import { test } from 'node:test';
import assert from 'node:assert/strict';
import { makeServer } from '../src/app.js';

test('sign in and out', async (t) => {
  const server = makeServer();
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  t.after(() => server.close());
  const base = `http://127.0.0.1:${server.address().port}`;

  const bad = await fetch(`${base}/login`, { method: 'POST', body: JSON.stringify({ email: 'ana@example.test', password: 'x' }) });
  assert.equal(bad.status, 401);

  const res = await fetch(`${base}/login`, {
    method: 'POST', body: JSON.stringify({ email: 'ana@example.test', password: 'correct horse' }),
  });
  assert.equal(res.status, 200);
  const sid = res.headers.get('set-cookie').split(';')[0];
  assert.equal((await fetch(`${base}/me`, { headers: { cookie: sid } })).status, 200);
  await fetch(`${base}/logout`, { method: 'POST', headers: { cookie: sid } });
  assert.equal((await fetch(`${base}/me`, { headers: { cookie: sid } })).status, 401);
});
