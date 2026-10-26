# crm-import

Imports contact CSV exports into the CRM's JSON store.

    node bin/import.js contacts.csv --db crm.json

The CSV has a header row `name,email,company`; fields may be quoted ("Acme, Inc.").
Run the tests with `npm test`.
