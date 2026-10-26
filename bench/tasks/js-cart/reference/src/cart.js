// All money is handled in integer cents. Prices in cart.json have at most two decimals.
export const TAX_BPS = 825; // 8.25% in basis points

export class CartError extends Error {}

const toCents = (price) => Math.round(Number(price) * 100);
// value / divisor rounded half up, for non-negative integers.
const divHalfUp = (value, divisor) => Math.floor((2 * value + divisor) / (2 * divisor));

export function totals(cart) {
  let subtotal = 0;
  for (const item of cart.items) subtotal += toCents(item.price) * item.qty;

  let discount = 0;
  const code = cart.code || '';
  let m;
  if (!code) discount = 0;
  else if ((m = /^PERCENT(\d+)$/.exec(code))) discount = divHalfUp(subtotal * Number(m[1]), 100);
  else if ((m = /^FIXED(\d+)$/.exec(code))) discount = Math.min(subtotal, Number(m[1]) * 100);
  else throw new CartError(`unknown discount code: ${code}`);

  const tax = divHalfUp((subtotal - discount) * TAX_BPS, 10000);
  return { subtotal, discount, tax, total: subtotal - discount + tax };
}

export const money = (cents) => `${Math.floor(cents / 100)}.${String(cents % 100).padStart(2, '0')}`;
