# catalog-api

A tiny JSON API over `data/items.json`, no dependencies.

    node server.js --port 3000
    curl 'localhost:3000/items?tag=red'
    curl localhost:3000/items/3

Run the tests with `npm test`.
