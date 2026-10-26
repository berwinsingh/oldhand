import { test } from 'node:test';
import assert from 'node:assert/strict';
import { totals } from '../src/cart.js';

test('no code: subtotal plus tax', () => {
  const t = totals({ items: [{ sku: 'A', price: 10, qty: 2 }] });
  assert.equal(t.subtotal, 20);
  assert.equal(t.discount, 0);
  assert.equal(t.total, 21.65);
});

test('FIXED5 takes five dollars off', () => {
  const t = totals({ items: [{ sku: 'A', price: 40, qty: 1 }], code: 'FIXED5' });
  assert.equal(t.discount, 5);
});
