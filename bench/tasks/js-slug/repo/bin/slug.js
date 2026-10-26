#!/usr/bin/env node
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { uniqueSlug } from '../src/slug.js';

const args = process.argv.slice(2);
const at = args.indexOf('--store');
const store = at >= 0 ? args.splice(at, 2)[1] : 'slugs.json';
const [cmd, title] = args;
const slugs = existsSync(store) ? JSON.parse(readFileSync(store, 'utf8')) : [];

if (cmd === 'add' && title !== undefined) {
  const slug = uniqueSlug(title, slugs);
  slugs.push(slug);
  writeFileSync(store, JSON.stringify(slugs, null, 2) + '\n');
  console.log(slug);
} else if (cmd === 'list') {
  for (const s of slugs) console.log(s);
} else {
  console.error('usage: slug.js add "<title>" | list  [--store file]');
  process.exit(2);
}
