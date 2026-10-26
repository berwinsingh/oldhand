#!/usr/bin/env node
import { readFileSync } from 'node:fs';
import { CartError, money, totals } from '../src/cart.js';

const [cmd, file] = process.argv.slice(2);
if (cmd !== 'total' || !file) {
  console.error('usage: cart.js total <cart.json>');
  process.exit(2);
}
let t;
try {
  t = totals(JSON.parse(readFileSync(file, 'utf8')));
} catch (e) {
  if (!(e instanceof CartError)) throw e;
  console.error(`error: ${e.message}`);
  process.exit(2);
}
console.log(`subtotal: ${money(t.subtotal)}`);
console.log(`discount: ${money(t.discount)}`);
console.log(`tax: ${money(t.tax)}`);
console.log(`total: ${money(t.total)}`);
