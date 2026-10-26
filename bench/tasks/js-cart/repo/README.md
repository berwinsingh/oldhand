# cart

Prices a shopping cart: subtotal, discount code, sales tax (8.25%) and total.

    node bin/cart.js total cart.json

`cart.json` looks like `{"items": [{"sku": "TEE", "price": 19.99, "qty": 2}], "code": "PERCENT10"}`.
Codes: `PERCENT<n>` takes n% off the order, `FIXED<n>` takes n dollars off.

Run the tests with `npm test`.
