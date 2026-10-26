Bug: a cart of 3 items at $0.10 prints `subtotal: 0.30000000000000004`, and some totals come out a cent off.

Expected behaviour of `node bin/cart.js total <cart.json>`:
- Money is exact to the cent, and every amount prints with exactly two decimals (`subtotal: 0.30`).
- `PERCENT<n>`: the discount is n% of the subtotal, rounded half up to the cent.
- `FIXED<n>`: n dollars off, but never more than the subtotal.
- Tax is 8.25% of the subtotal after the discount, rounded half up to the cent.
- Total = subtotal - discount + tax.
- An unknown discount code is an error: exit code 2 and a message on stderr naming the code.
- Keep the four output lines and their order: `subtotal`, `discount`, `tax`, `total`.
