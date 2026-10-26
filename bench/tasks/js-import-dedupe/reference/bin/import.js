#!/usr/bin/env node
import { readFileSync } from 'node:fs';
import { newContacts } from '../src/dedupe.js';
import { normalize, validEmail } from '../src/normalize.js';
import { parseCsv } from '../src/parse.js';
import { load, save } from '../src/store.js';

const args = process.argv.slice(2);
const at = args.indexOf('--db');
const db = at >= 0 ? args.splice(at, 2)[1] : 'crm.json';
const [file] = args;
if (!file) {
  console.error('usage: import.js <contacts.csv> [--db crm.json]');
  process.exit(2);
}
const valid = [];
let invalid = 0;
parseCsv(readFileSync(file, 'utf8')).map(normalize).forEach((row, i) => {
  if (validEmail(row.email)) valid.push(row);
  else {
    invalid += 1;
    console.error(`row ${i + 1}: invalid email`);
  }
});
const existing = load(db);
const { added, skipped } = newContacts(valid, existing);
if (added.length) save(db, [...existing, ...added]);
console.log(`added ${added.length}, skipped ${skipped}, invalid ${invalid}`);
