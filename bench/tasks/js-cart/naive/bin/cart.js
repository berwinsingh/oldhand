#!/usr/bin/env node
import { readFileSync } from 'node:fs';
import { totals } from '../src/cart.js';

const [cmd, file] = process.argv.slice(2);
if (cmd !== 'total' || !file) {
  console.error('usage: cart.js total <cart.json>');
  process.exit(2);
}
const t = totals(JSON.parse(readFileSync(file, 'utf8')));
console.log(`subtotal: ${t.subtotal.toFixed(2)}`);
console.log(`discount: ${t.discount.toFixed(2)}`);
console.log(`tax: ${t.tax.toFixed(2)}`);
console.log(`total: ${t.total.toFixed(2)}`);
