import { test } from 'node:test';
import assert from 'node:assert/strict';
import { newContacts } from '../src/dedupe.js';
import { parseCsv } from '../src/parse.js';

test('parses quoted fields', () => {
  const rows = parseCsv('name,email,company\n"Coyote, W.",w@acme.test,"Acme, Inc."\n');
  assert.deepEqual(rows, [{ name: 'Coyote, W.', email: 'w@acme.test', company: 'Acme, Inc.' }]);
});

test('skips an email already in the store, in any case', () => {
  const out = newContacts([{ email: 'A@x.test' }, { email: 'b@x.test' }], [{ email: 'a@x.test' }]);
  assert.deepEqual(out, { added: [{ email: 'b@x.test' }], skipped: 1 });
});
