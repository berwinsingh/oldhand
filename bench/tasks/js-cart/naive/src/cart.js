export const TAX_RATE = 0.0825;

export function totals(cart) {
  let subtotal = 0;
  for (const item of cart.items) subtotal += item.price * item.qty;

  let discount = 0;
  const code = cart.code || '';
  if (code.startsWith('PERCENT')) discount = (subtotal * Number(code.slice(7))) / 100;
  else if (code.startsWith('FIXED')) discount = Number(code.slice(5));

  const tax = (subtotal - discount) * TAX_RATE;
  return { subtotal, discount, tax, total: subtotal - discount + tax };
}
