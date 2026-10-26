import { test } from 'node:test';
import assert from 'node:assert/strict';
import { money, totals } from '../src/cart.js';

test('no code: subtotal plus tax, in cents', () => {
  const t = totals({ items: [{ sku: 'A', price: 10, qty: 2 }] });
  assert.equal(t.subtotal, 2000);
  assert.equal(t.discount, 0);
  assert.equal(money(t.total), '21.65');
});

test('FIXED5 takes five dollars off', () => {
  const t = totals({ items: [{ sku: 'A', price: 40, qty: 1 }], code: 'FIXED5' });
  assert.equal(t.discount, 500);
});

test('three dimes are thirty cents', () => {
  assert.equal(money(totals({ items: [{ sku: 'A', price: 0.1, qty: 3 }] }).subtotal), '0.30');
});
