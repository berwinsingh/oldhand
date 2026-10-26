import { test } from 'node:test';
import assert from 'node:assert/strict';
import { makeServer } from '../app.js';

async function get(server, path) {
  const { port } = server.address();
  const res = await fetch(`http://127.0.0.1:${port}${path}`);
  return { status: res.status, body: await res.json() };
}

test('the API', async (t) => {
  const server = makeServer();
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  t.after(() => server.close());

  await t.test('lists every item', async () => {
    const { status, body } = await get(server, '/items');
    assert.equal(status, 200);
    assert.equal(body.length, 6);
  });
  await t.test('filters by one tag', async () => {
    const { body } = await get(server, '/items?tag=cotton');
    assert.deepEqual(body.map((i) => i.id), [1, 2, 3]);
  });
  await t.test('fetches one item, 404 for a missing one', async () => {
    assert.equal((await get(server, '/items/3')).body.name, 'Tee, blue, L');
    assert.equal((await get(server, '/items/99')).status, 404);
  });
});
