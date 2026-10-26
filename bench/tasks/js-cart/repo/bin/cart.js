#!/usr/bin/env node
import { readFileSync } from 'node:fs';
import { totals } from '../src/cart.js';

const [cmd, file] = process.argv.slice(2);
if (cmd !== 'total' || !file) {
  console.error('usage: cart.js total <cart.json>');
  process.exit(2);
}
const t = totals(JSON.parse(readFileSync(file, 'utf8')));
console.log(`subtotal: ${t.subtotal}`);
console.log(`discount: ${t.discount}`);
console.log(`tax: ${t.tax}`);
console.log(`total: ${t.total}`);
