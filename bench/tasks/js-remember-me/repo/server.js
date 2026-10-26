#!/usr/bin/env node
import { makeServer } from './src/app.js';

const at = process.argv.indexOf('--port');
const port = at >= 0 ? Number(process.argv[at + 1]) : 3000;
const server = makeServer();
server.listen(port, '127.0.0.1', () => console.log(`listening on ${server.address().port}`));
