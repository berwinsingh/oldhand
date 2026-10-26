#!/usr/bin/env node
import { readFileSync } from 'node:fs';
import { newContacts } from '../src/dedupe.js';
import { normalize } from '../src/normalize.js';
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
const rows = parseCsv(readFileSync(file, 'utf8')).map(normalize);
const existing = load(db);
const added = newContacts(rows, existing);
save(db, [...existing, ...added]);
console.log(`added ${added.length}`);
